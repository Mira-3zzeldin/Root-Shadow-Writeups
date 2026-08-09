---
title: "Security Principles - Part I: Trust Is Not a Feeling"
seoTitle: "Trust-Security: Why Systems Need Evidence, Not Assumptions"
seoDescription: "Learn why secure systems verify evidence instead of trusting claims, through lessons from a biometric fintech wallet and Zero Trust design."
datePublished: 2026-05-19T14:01:30.092Z
cuid: cmpcpbiej005j2dn8em7x1sv8
slug: security-principles-trust-is-not-a-feeling
cover: https://cdn.hashnode.com/uploads/covers/6a0330ea937b84f77988ba5d/d640b763-2949-464e-8054-52c9cc62048e.png
ogImage: https://cdn.hashnode.com/uploads/og-images/6a0330ea937b84f77988ba5d/009820d0-9f31-4f6b-bc64-ffeb46280c47.png
tags: software-architecture, cybersecurity, application-security, zerotrust, secure-coding, securityengineering

---

> *This article explores one of the most fundamental ideas in security: why systems should trust evidence instead of assertions, illustrated through real design decisions from my graduation project, InstaShield.*

## What the System Actually Believes

At some point during every payment transaction flow, the server is faced with a decision — authorize the payment or not. Everything else — logging in, scanning, session tokens — all this is just information used by the server to make that decision. The real question then isn't "Is the system secure?" It's narrower and more useful: **When the server decides to move money, what is that decision actually based on?**

I didn't start from there. I start with a bug.

## The assumption that looked fine

In the early days of InstaShield, the code for payment confirmation looked something like this:

```javascript

if (matched === true) {
    PaymentAuth();
}
```

`matched` was delivered by the biometric service — a standalone hardware terminal (ZK fingerprint scanner) — over the network, to the payment service. On paper, this seemed sensible: scan fingerprint, compare with template stored in server, get result, authorize payment if match.

But the issue was not the condition — it was performing exactly its intended function. The issue was that the data being evaluated had already passed the trust boundary by the time the payment service received it. All `matched: true` means is two words within a JSON body. It doesn't tell you anything about where the data came from. Anyone with the knowledge to recognize the structure of the request can bypass the biometric scan completely and make the payment directly. The test wasn't confirming identity — it was confirming the truthiness of a single boolean variable.

That's the point at which the important question emerged, and it would become one of four core questions asked repeatedly through the system design: **Where did this information actually come from, and can that origin be verified — or only assumed?**

* * *

## Origin: a claim is not its own evidence

That was when the new trust model came into play. The boolean parameter was stripped away from the API - not merely hidden, but completely removed as a concept. Consequently, the controller simply presents a `matchProof` parameter: an HMAC-SHA256 signature of the fingerprint ID and timestamp, generated using a shared secret. The payment service recomputes this value independently, and discards the entire request if the verification fails.

This small change in the code is a big change in terms of trust. Previously, the payment service asked, "What did the biometric service say?" Now it asks, "Can I independently verify what the biometric service said?" These questions sound similar but are worlds apart. The first is something anyone who can shape a request can answer. The second involves a cryptographic relationship between two trusted components — one the client has no access to, even if it fully controls the request body.

This is the key case of an issue that kept recurring everywhere else within the system: trust is not extended on the assumption that a component is being honest; rather, it is made unnecessary through requiring evidence.

The same logic governs how InstaShield treats its real-time payment channel. A WebSocket connection is authenticated, encrypted, and genuinely tied to the right session — but none of that says anything about whether a specific message sent over it is true. A message announcing "payment confirmed" arriving over a trusted connection is still just an assertion carried by that connection, not proof of the state it describes. So the server doesn't treat the content of a WebSocket message as a fact to act on. It treats it as a knock at the door — a signal to go check — and only confirms the actual payment state through a separate, independently authenticated HTTPS request. The channel being secure was never the same claim as the message being true, and collapsing those two would have reintroduced the exact problem the matchProof change was built to remove, just on a different transport.

The interesting part, looking back, is that the system wasn't failing because these checks were missing. It was failing because it had quietly decided who deserved to be believed.

* * *

## Time: proof of identity settled, but settled *when*?

Origin was just the first dimension. The problems were arising during payment system development, but none of the questions were particular to payments — it applies to virtually any system that handles information across a trust boundary. Even when the claim is eventually traced to a trusted source, there is another, less obvious assumption behind it: the fact that was true once will remain true.

Status of KYC would be an example here. The user could be KYC'ed when he starts the payment transaction, but his KYC status would be immediately revoked, seconds later, before the payment transaction confirms. When the system does the verification only once at the start of transaction, the window appears that can be exploited — the transaction that has all the appearances of legitimate one is based on false fact that becomes false before the money gets transferred.

InstaShield verifies the KYC status of users twice: first, when they start the payment; and second, when the payment confirms. It is a simple control measure. But it has the same origin as `matchProof` change, but on different axis: **A fact can be considered only as valid as the point when it was verified for the last time.** Making such verification the ultimate truth will be the very case of the unproven statement, which is proven incorrect over time instead of by an attack.

JWTs are processed following this principle as well. The first assumption was that the validity of a token means the validity of the user state. However, the token itself is just a snapshot, and the claims it contains relate to the state of the user at the time when the token was issued. And the middleware does not just read these claims; it makes a live validation of `user.status === 'active'` on every request, because the issue of whether the snapshot reflects the reality or not is a separate issue.

* * *

## Boundary: does verification travel with the request?

The origin and the time of the claim both assume that the evaluation happens within the same element that eventually acts on the claim. Yet, most applications aren't constructed that way. The request goes through a controller, through a service, possibly even through a downstream call, and there's a temptation to see the whole pipeline as a verified one. If the controller verified the auth, then the service layer just... proceeds.

The method `paymentService.initiatePayment` does not proceed under this assumption. Instead of assuming that the authorization was verified in the previous step and just inhering it without verification, it verifies `callerUserId === merchant.userId`.This ensures that even if a user is authenticated at the controller level, they cannot perform actions on behalf of another merchant. This is what we call the third dimension: **verification doesn't follow a request because it was performed further up the call stack.** Authorization is not a gate that you've gone through once – it is a claim that you need to verify again and again.

* * *

## Context: valid, but valid *for whom*?

Then there is a fourth dimension, which may be overlooked because the claim itself has already survived the previous three tests. The `matchProof` may indeed be a cryptographically sound proof, that is, correctly signed and new and definitely coming from the biometric service, but it could be the wrong proof for this transaction.

Thus, in addition, the server verifies `userId === intent.userId` before doing any credits. Just a valid proof wasn't enough; it needed to be valid **and** relevant. The origin tells you that the claim is trustworthy. The context tells you that the claim is relevant.

* * *

## Applying the same four questions outside the payment decision

Once these questions became explicit, I began to see similar issues of trust that arose beyond the payment decision itself — specifically around how the system validated the identity with which it was trying to communicate.

This becomes clear in relation to the kiosk component. The physical machine and the mobile application are each, in a certain way, "authenticated"; however, the authentication happens in very different identity spaces. The kiosk is authenticated as a device, whereas the mobile application is authenticated as a user. To merge them into one identity space would mean that a compromise in either one secretly opens up the other to trust (for example, an attacker compromising the public kiosk could gain implicit access to the user's mobile session). Instead, one secret is used as a bridge between the two separate identities — binding the single transaction context without blending their access rights.

Certificate pinning presents the same challenge at the network level: who am I communicating with? An SSL certificate is only ever authenticated by a trusted certificate authority; there is no requirement that it be signed by the trusted certificate authority that InstaShield assumes it is communicating with. Without pinning, an attacker could intercept the traffic using a completely different, yet legally valid, certificate issued for another domain. To prevent this, the app validates the expected public key hash **of our specific server**; otherwise, it simply refuses to run in release mode.

* * *

## The principle underneath all of it

None of them are anything exotic either. A signature validation, a status check, an extra authorization check – all seem trivial separately. The power of each lies not in the control itself but in the assumption which it removes from the equation.

In retrospect, any act of trust in the system was boiled down to four things:

*   **Origin** – who signed this claim?
    
*   **Time** – is it true right now?
    
*   **Boundary** – will it hold on crossing the layer boundary?
    
*   **Context** – is it relevant for this particular user, transaction, request?
    

The inability to answer those questions leaves a system no choice but to default to trusting and hope nothing takes advantage of it. The ability to answer those questions means the shift of the burden of proof to the claimant – client, token, previous layer, proof itself – rather than to the system of trust.

It's not something that only applies to biometric payment methods. Modern systems are replete with claims being made across borders — from tokens to APIs, from services to devices and users — and at every border, "It's true somewhere else" becomes "It's true here." This act of translation changes the very meaning of "secure." Security is not some quality the system possesses; it's an ideal the system upholds for all claims, including its own.

The moment I began viewing each and every trust assertion as an assumption needing evidence to back it up, it became clear that the logical next step would be to abandon that assumption and attempt to shatter it.

* * *

**Series:** Security Principles — Part I of VI

**Next:** Threat Modeling — thinking like the attacker on purpose