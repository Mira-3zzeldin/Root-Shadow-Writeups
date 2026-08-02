---
title: "Security Principles - Part I: Trust Is Not a Feeling"
seoTitle: "Trust-Security: Why Systems Need Evidence, Not Assumptions"
seoDescription: "Learn why secure systems verify evidence instead of trusting claims, through lessons from a biometric fintech wallet and Zero Trust design."
datePublished: 2026-05-19T14:01:30.092Z
cuid: cmpcpbiej005j2dn8em7x1sv8
slug: security-principles-trust-is-not-a-feeling
ogImage: https://cdn.hashnode.com/uploads/og-images/6a0330ea937b84f77988ba5d/009820d0-9f31-4f6b-bc64-ffeb46280c47.png
tags: software-architecture, cybersecurity, application-security, zerotrust, secure-coding

---

> *This article explores one of the most fundamental ideas in security: why systems should trust evidence instead of assertions, illustrated through real design decisions from my graduation project, InstaShield.*

There's a line in an early draft of my graduation project's API that I still think about.

```json
POST /fingerprint/confirm

{
  "fingerprintId": "fp_8821",
  "matched": true
}
```

That's it. That's the whole authorization. The mobile app talked to the ZK9500 reader, ran its match, and told the server the answer. The server believed it. Wallet credited, transaction closed, receipt printed.

At the time this felt completely reasonable. The fingerprint reader had already done the hard part — the biometric comparison, the templates, the minutiae points, whatever cryptography I assumed lived somewhere in that pipeline. By the time `matched: true` reached my backend, the scary work was finished. My server's job was just to record the outcome.

I didn't think of this as trusting the client. I thought of it as respecting a division of labor.

It took a threat-modeling session — the kind where you sit down and deliberately ask "how would I attack this if I were the adversary" instead of "does this work" — to notice what that boolean actually was.

It wasn't a fact arriving at my server.

It was **a claim**.

And nothing distinguishes an honest claim from a forged one, syntactically. `{"matched": true}` sent by a phone that just ran a real fingerprint scan is byte-for-byte identical to `{"matched": true}` typed into Postman by someone who has never touched the reader. My server had no way to tell the difference, because I'd never given it one.

This is the part that's uncomfortable to sit with: a server doesn't experience the world. It doesn't see the fingerprint reader or feel the finger on the sensor — all it has is bytes arriving over a socket. Every single thing your backend "knows" is actually just something a client asserted. Authentication headers, request bodies, TLS client certificates — all of it is testimony, not observation.

> The server is a judge who was never at the scene, ruling entirely on what witnesses say happened.

Once you see it this way, "trust" stops being a binary property a system either has or doesn't. It becomes an evidentiary question. Not *do I trust this request* but *what evidence does this request carry, and is that evidence something only the legitimate actor could have produced?*

That reframing is the whole difference between a secure system and one that merely looks secure.

* * *

## Evidence, Not Assertions

Here's what changed in InstaShield once that clicked. The boolean disappeared from the API entirely — not hidden, not double-checked, *removed as a concept*. In its place, the fingerprint controller now produces:

```javascript
const matchTimestamp = Date.now();

const matchProof = crypto
  .createHmac('sha256', fingerprintMatchSecret)
  .update(${fingerprintId}.${matchTimestamp})
  .digest('hex');
```

The implementation details are straightforward: create a short-lived proof bound to a specific fingerprint identity and timestamp. The important security change is not the HMAC call itself — it is removing the need to trust an unsigned decision from the client.

The client still tells the server a match happened. But now it can't just say so — it has to produce a value that only someone in possession of a server-side secret could have generated. On the way back through the payment flow, the backend recomputes that `HMAC` independently, using its own copy of the secret, and does a constant-time comparison against what arrived. If they match, the server hasn't been told the truth — it has *derived* the truth, using the same math the legitimate flow would have used and nothing else. Since the secret never leaves the server, a forged client cannot generate a valid proof even if it completely controls the request body.

That's the actual shape of the fix, and it's worth noticing what it isn't. It isn't "check the boolean twice." It isn't "validate the input more carefully." Those are patches on a claim-based model — you're still just trusting the assertion, only now with a spell-checker. The fix works because it changes what kind of thing is being sent at all. A claim became evidence. And evidence, unlike a claim, is something a verifier can check without having to trust the party presenting it.

* * *

## Trust Has an Expiration Date

I added one more constraint almost as an afterthought that turned out to matter more than I expected: the proof expires. A sixty-second window, checked against the timestamp embedded in the signed payload, with rejection for anything too old *or* — and this took me a moment to understand why it mattered — anything claiming to be from the future. That second check isn't paranoia for its own sake. If your only rule is "reject old timestamps," an attacker who can influence clock skew, even slightly, has room to maneuver. Rejecting future timestamps closes that off. A signature intercepted and replayed five minutes later is now just as useless as one that was never valid, because the evidence has an expiration date baked into the math itself.

That detail is what finally made me understand that trust isn't just about *whether* to believe a claim. It's about *for how long*, and *under what conditions*. A valid `HMAC` one minute after issuance and the identical `HMAC` an hour later are, cryptographically, the exact same string — but only one of them is still evidence. **Trust has a shelf life,** and a system that doesn't enforce one has quietly decided to trust forever, which is a much bigger decision than anyone intended to make.

## Trust Boundaries

The other thing this forced me to confront was where, exactly, my trust boundaries actually were — as opposed to where I'd assumed they were.

I had drawn a mental line around "the client," as if that were one coherent thing. It's not. The Flutter app, the WebSocket channel it uses to receive payment status, the local biometric hardware, the physical kiosk devices in a merchant setting, even the payload announcing *that a payment succeeded* — each of these is a separate boundary with its own evidentiary requirements. The WebSocket case was the one that embarrassed me most. It seemed obviously fine — the server pushes a `payment_result` message down an authenticated socket, the client displays it. What could go wrong?

What could go wrong is that the socket's authenticity guarantees the *connection*, not the *content*. And a payment result carries financial weight that a chat message doesn't. So the boundary got redrawn: the WebSocket message became advisory only — a "something happened, go check" signal — and the client re-verifies the actual transaction state over a separate, pinned HTTPS call before it shows anyone a success screen. The socket got demoted from "source of truth" to "doorbell." It still does useful work. It just isn't asked to do work it was never actually capable of doing.

> **Key idea**
> 
> A secure communication channel does **not** automatically make its content authoritative.

I think this is where a lot of security thinking goes wrong for beginners, myself included: we imagine there's one trust boundary — the login screen, maybe, or "does this have a valid token" — and once you're past it, everything inside is fine. Real systems don't have an inside. They have a mesh of boundaries, one at every point where an assertion crosses from a context where it *could* be false into one where it's about to be acted on as if it's *true*. Every crossing deserves its own answer to "why does this system believe this," and the answer can differ each time — a signature, a re-derivation from a secret, or simply a channel being refused permission to assert something it was never built to prove.

## Zero Trust Is Just Verified Trust

By the time I'd redrawn this many boundaries — the fingerprint proof, the WebSocket demotion, the kiosk devices carrying their own shared secret instead of a free pass — I realized I'd already arrived at something with a name I'd been avoiding: zero trust. The term gets thrown around often enough that it's started to sound like a marketing phrase instead of an engineering stance. But the idea underneath it was exactly what every one of these fixes had in common: stop asking whether something is inside or outside your perimeter, and start asking what evidence it's carrying. A request from your own authenticated mobile app, on a device you issued, over a channel you pinned, still doesn't get a free pass — it still has to prove the specific thing it's claiming, every time, because the alternative is deciding in advance that some category of requester is simply incapable of lying or being compromised. Nothing is. Not your client. Not your database. Not, honestly, your own code from six months ago, which is a separate and slightly humbling lesson.

## Key Takeaways

*   Every request is a claim.
    
*   Claims are not evidence.
    
*   Trust must be verified.
    
*   Trust has boundaries.
    
*   Trust expires.
    
*   Zero Trust is verified trust.
    

## The Question Behind Every System

What I keep coming back to is that none of this was really about fingerprints, or HMACs, or even fintech. Those were just the specific vocabulary this project happened to use. The underlying question — *why does the system believe this* — is the same question whether you're looking at a biometric match, an OAuth scope, a webhook signature, or a coworker's Slack message asking you to push to production. Some claims deserve to be believed. But they deserve it because of evidence you can independently check, not because of who's making the claim, or how confident they sound, or how reasonable the request seems in the moment.

Every security system eventually answers the same question — *why does this system believe this* — and everything else is just an implementation detail.

## Security Principles Series

*   **Part I — Trust Is Not a Feeling** ← You are here
    
*   **Part II — Threat Modeling: Finding What the System Assumes** *(Coming Soon)*
    
*   **Part III — Secure Design: Building Systems That Fail Safely** *(Coming Soon)*
    
*   **Part IV — Trust Boundaries: Where Should We Stop Trusting?** *(Coming Soon)*
    
*   **Part V — Security Trade-offs: What We Choose Not To Solve Yet** *(Coming Soon)*