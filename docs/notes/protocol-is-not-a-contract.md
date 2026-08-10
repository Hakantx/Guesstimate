# A protocol is not a contract

This project defines a game as an interface with two implementations. One plays
entirely in memory, for the CLI and for offline play on a phone; the other talks
to a server over HTTP. Both satisfy the same protocol, both type-check under
mypy in strict mode, and for a while both were wrong about the same thing in
different directions.

## The interface

The protocol is small. A game exposes its state, the candidates still possible,
and — depending on the mode — a way to play a code or to answer the solver. The
one that answers the solver is documented to raise a particular exception when
the answer contradicts something said earlier, because a person scoring a game
by hand gets that wrong regularly and the caller is expected to apologise and
ask again rather than start over.

The local implementation does exactly that. It hands the answer to the solver,
the solver refuses it, and the exception propagates untouched.

## What the second implementation did instead

The remote implementation sends the answer to a server, which hands it to the
same solver, which raises the same exception. The server catches it and returns
HTTP 409, because the request was well-formed and merely contradicted the
conversation. The client sees a failed response and raises whatever an HTTP
library raises for a failed response.

So a caller written against the interface — catching the contradiction and
offering a correction — works perfectly against the local game and breaks
against the remote one. Not with a wrong answer, which might get noticed, but
with an unhandled exception of an entirely different type escaping from a
method that was documented to raise something else.

Every static check passed. The method signatures match, the return types match,
mypy is content, and it is content correctly: **exceptions are not part of a
Python type**. Nothing in the protocol declaration says what may come out of a
method sideways, so nothing can check that two implementations agree about it.
The docstring says it. The docstring is prose.

## Why the tests did not catch it either

The API had thorough tests. They checked that a contradiction returns 409, that
the game survives one, that the board is unchanged afterwards. All passing, all
correct, and all written from the server's point of view — they assert what the
*endpoint* does, never what a *caller of the interface* experiences.

The local game had equally thorough tests asserting the exception. Also passing.
Two well-tested implementations, one protocol, and a gap that neither test suite
was looking at because each was looking at its own side.

What found it was playing the same seeded games through both implementations
and comparing them turn by turn. The gate was built to catch the two sides
diverging on *results*; it caught them diverging on *failures*, which is a
category nobody had thought to check. Writing the client was what surfaced it —
the moment there was a second implementation, the question "what does this raise"
had two answers.

## The fix, and the shape of it

The server now names its failures. Every refusal carries a machine-readable
code, and the client keeps a table mapping each code to exactly one exception.
A contradiction over the wire raises the same exception as a contradiction in
memory, so a caller written against the interface behaves identically either
way.

The first attempt was a boolean — `recoverable: true` on the response — which
worked while there were exactly two failures to tell apart and quietly encoded
the assumption that there always would be. It also made the client *infer* which
exception was meant from a flag that answered a different question. A code maps
one to one, extends by adding a member, and when the client meets a code it does
not know it raises a loud unknown rather than guessing.

## What to take from it

**A protocol constrains shape, not behaviour.** Matching signatures are the
cheapest half of an interface. What a method does when it fails, what it
guarantees about state after a failure, whether it is idempotent, what it does
when called out of order — none of that is in the type, and all of it is what a
caller depends on.

**One implementation of an interface is not an interface.** It is one
implementation with a type annotation on it. Every assumption it happens to make
becomes part of the contract silently, and the first time a second
implementation appears, the assumptions surface as bugs. The cost of writing the
second implementation early is small; the cost of finding this in a browser,
against a deployed server, with a UI in between, is not.

**Equivalence tests should cover failure paths, not just results.** A gate that
only compares successful games proves the implementations agree about the easy
half. This one now plays the same games, compares the transcripts, *and* asserts
that the same mistakes raise the same exceptions on both sides.

This is the second real bug an equivalence gate has caught in this project. The
first was two partitioners disagreeing about a tie-break because floating-point
addition is not associative, which every outcome-based test passed. Both were
invisible to tests that checked each implementation on its own terms, and both
took about ten minutes to find once something compared the two directly.
