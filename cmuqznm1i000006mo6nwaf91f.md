---
title: "Security Principles - Part 3: Hardcoding the Safe Zones"
seoTitle: "Secure by Design: Decisions Have to Exist Before Problems"
seoDescription: "Breaking down the architectural decisions in a biometric fintech payment system that were made before any vulnerability forced them."
datePublished: 2026-09-10T07:30:00.000Z
cuid: cmuqznm1i000006mo6nwaf91f
slug: security-principles-hardcoding-the-safe-zones
cover: https://cdn.hashnode.com/uploads/covers/6a0330ea937b84f77988ba5d/bcaa3f61-e616-4b85-9729-bc41c7de6688.png
ogImage: https://cdn.hashnode.com/uploads/og-images/6a0330ea937b84f77988ba5d/3194503f-01f5-48d9-a11b-bde69eb34c50.png
tags: cybersecurity, application-security, secure-coding, security-engineering, secure-by-design

---

> This article explores one of the most fundamental ideas in security: why secure code cannot save a broken architecture, illustrated through real secure-by-design choices from my graduation project, InstaShield.

## Which Decisions Had to Exist Before the Problem Did

Most of the fixes in Part II had a shape in common: something worked, an attacker's question exposed what it actually trusted, and the system changed in response. That's a real and necessary process. It's also, by definition, reactive, the decision to fix the JWT verification call only existed because the gap had already been found.

Not every decision in InstaShield followed that shape. Some of them were never reactions to anything. They were choices made before there was an incident to react to — before a vulnerability, before an attacker, sometimes before there was even working code to test. The question behind them wasn't "how do we fix this." It was: **which decisions have to exist before the problem does?**

Secure by Design is not about having fewer vulnerabilities. It is about making critical security decisions before the system forces you to make them.

* * *

## Refusing to start is a design decision, not a bug fix

The clearest example is also the least dramatic one. If a required cryptographic key or secret is missing when InstaShield's services start, they don't start in a degraded or default state. They terminate — `process.exit(1)` on the Node side, a `RuntimeError` on the Python side — immediately, before handling a single request. The important decision was not how the service handles a missing secret. It was deciding that a service without that secret is not a valid state of the system in the first place.

The alternative is allowing the application to start while relying on warnings, fallback values, or operational assumptions. That failure mode doesn't announce itself. It sits quietly in production until someone — usually an attacker — finds the gap it left behind.

Fail-fast startup isn't a patch for a specific vulnerability. There's no CVE behind it, no incident it was written in response to. It's a decision about what the system is allowed to consider "running" at all, made before deployment, independent of any particular attack. The distinction matters: a fix closes a path someone already found. A design decision like this one removes an entire category of path before anyone gets the chance to look for it.

* * *

## Deciding what a breach is allowed to cost, in advance

The same before-the-fact posture shows up in how secrets are structured. InstaShield doesn't use one global secret for everything that needs signing or verification — it uses five, one per trust domain, so that a device-level secret and a user-session secret and an inter-service secret are never the same value. The goal wasn't to make secrets easier to manage. It was to prevent one compromised trust domain from becoming a shortcut into every other one.

This only matters in a scenario that, ideally, never happens: one of those secrets leaking. If it does, the question that was already answered is *how much does this one leak actually cost us?* With a single shared secret, the answer is everything. With five domain-separated secrets, the answer is whatever that one domain was responsible for, and nothing else. Nobody had to discover this the hard way for the decision to exist. The blast radius was defined before there was anything to explode.

* * *

## Two systems, one fact, and the same signature

Domain separation only works if the systems on either side of the boundary agree on what they're signing. That turned out to be its own design problem. When the Dart mobile app and the Node.js backend exchange data, they don't look at JSON the same way. By default, key ordering can differ between languages — Dart might output {"a":1, "b":2} while Node serializes it as {"b":2, "a":1}. Even though the logical facts are identical, an HMAC computed over two different byte representations produces two completely different signatures, quietly breaking valid requests.

The fix wasn't a complex runtime library to force coordination. It was a strict architecture rule established before writing code: both sides must sort JSON keys into alphabetical order prior to serialization. This ensures they independently arrive at the exact same byte representation. This isn't a security control in the usual sense — nothing here blocks an attacker directly. But it's exactly the kind of decision this article is about: a subtle correctness assumption (that two platforms agree on "the same data") that would have quietly undermined every HMAC check in the system if it hadn't been settled before the cross-platform signing ever went live.

* * *

## Assuming the database will eventually be exposed

Biometric templates are the most sensitive data in InstaShield, so their protection assumes the worst-case scenario. Instead of storing them raw and waiting for a compliance audit to mandate encryption, they are encrypted with Fernet from day one. The architecture is built on a simple premise: a database compromise is a scenario the system must survive, not a scenario we hope never happens.

This framing changes the outcome of a breach. If an attacker successfully dumps the database, the stolen rows are useless. The confidentiality of the biometric material survives even when the storage layer falls. The design doesn't just react to a threat; it fully expects it.

However, as Part VI will reveal, this assumption was fiercely challenged during the graduation defense — forcing a complete rethink of how biometric data should be handled when encryption alone isn't enough.

* * *

## Security without unnecessary exposure

Not every architecture choice is about fighting off a breach. Some are simply about minimizing your attack surface from the start. Request body limits are a perfect example. Using a single global limit for the entire app forces a bad trade-off: you either restrict every route to a small payload — which breaks legitimate large uploads — or you open the door wide everywhere. Raising the limit globally hands every single route a larger memory-exhaustion surface than it ever needs.

InstaShield solves this by scoping the body parser per context. Ordinary routes are strictly capped at 10KB. Only the specific endpoints that genuinely need to handle larger uploads are allowed up to 18MB. This isn't a reaction to an ongoing attack. It’s a design-time decision to ensure the size of the door always matches what is actually expected to walk through it.

* * *

## Designing for the failure, not just the success

Secure by design isn't only about anticipating attackers. Some of it is about anticipating the system's own ordinary failure modes — retries, dropped connections, concurrent requests — before they turn into something an attacker can exploit.

Payment settlement is a good example. A network retry, a duplicate webhook, a user double-tapping "confirm" — all of these can cause the same settlement request to arrive twice. The settlement logic checks whether the payment intent is already `SETTLED` before applying credit, which means a repeated request isn't a special case that needs special handling later — it's a state the operation was built to tolerate from the start. Nobody had to find a duplicate-credit bug in production for this to exist; the operation was designed to be safe to repeat before it was ever run once.

* * *

## The principle underneath all of it

What separates these cases from the ones in Part II isn't severity, and it isn't mechanism — a body limit and a signature check aren't fundamentally different kinds of code. What separates them is *when the decision was made relative to the problem it addresses.* A fix exists because a gap was found. A design decision exists because someone assumed the gap was possible before anything confirmed it.

That distinction is easy to blur in hindsight, because both eventually show up as a few lines in the codebase. But they come from different questions. Threat modeling asks: *given this system, how could it be abused?* Secure by design asks something earlier: *before this system exists in its current form, what has to be true about it regardless of what we later discover?* Fail-fast startup, key separation, canonical serialization, encrypted templates, idempotent settlement — none of these controls were written in response to an attacker. They were written in response to the possibility of one, which is a very different kind of motivation, and a much harder habit to build.

A security control is not automatically Secure by Design just because it exists. The question is whether the decision existed before the problem that it protects against. A rate limit added after a scraping incident is a good control — but it's a fix. The same rate limit, planned into the API from its first version because someone asked "what happens if this gets hit too often" before it ever did, is a design decision. The code can look identical. The timing is what makes the difference.

Not every one of those upfront decisions is free, though. Domain-separated secrets mean more key management. Fail-fast startup means an outage where a softer system might have limped along. Encrypting templates before storage adds a decryption step to every legitimate read. Secure by design doesn't mean security without cost — it means deciding, deliberately and early, which costs are worth paying before anyone is forced to find out.

Security maturity is not measured by how quickly a system reacts after failure. It is measured by how many failures the system was designed not to depend on surviving.

* * *

### Architecture Reference & Verification

The production-grade security architecture, strict verification matrices, and complete compliance maps referenced in this article series are published as an open reference.

Explore the public-safe repository here: 🔗 [InstaShield Security Architecture on GitHub](https://github.com/Mira-3zzeldin/InstaShield-Security-Architecture)

* * *

**Series:** Security Principles — Part III of VI

**Previous:** A System is Not its Intended Use — how can this be abused?

**Next:** A Perfect System Is a Fiction — what we left unresolved, and why?