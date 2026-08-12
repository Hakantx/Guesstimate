# The test that looked for the secret

The game server keeps the answer to itself until the game ends. Post-game
analysis grades each guess against what was available at the time, and it can
be shown mid-game, because it is computed from what the player has already been
told and reveals nothing they could not work out themselves.

That last claim wanted a test. The obvious one:

```python
body = client.get(f"/game/{game_id}/analysis").text
assert "123" not in body        # "123" being the secret
```

It failed immediately, and the failure was correct.

## Why it failed

Part of the analysis names the best guess available at each position — the one
that would have left fewest candidates standing. That code is computed from the
transcript alone. Sometimes it happens to be the secret.

Nothing has leaked. A player looking at their own board could run the same
calculation and get the same answer; the server has told them nothing they did
not already have. The secret's *digits* appear in the response, and the
secret's *value* had no part in producing it.

The test could not tell those apart, because it was not looking at the thing it
claimed to be checking. It was looking for a string.

## Proxy and property

"The secret does not leak" is a statement about **influence**: the output must
not depend on the hidden value. "The secret's digits are absent from the
response" is a statement about **content**, and the two come apart in both
directions.

They come apart the way this test found — content present, no influence, and
the test fails on correct code. That is the survivable direction, because
somebody investigates.

They also come apart the other way, which is worse. An analysis that leaked
badly — that ranked the true secret first, or subtly ordered candidates by
distance from it — would put no forbidden substring anywhere. Every digit in the
response would be one the player had already seen. The proxy test passes, the
property is violated, and nothing ever says so.

A passing proxy test is the failure mode worth worrying about. This one only
got noticed because it happened to fail.

## The test that checks the property

Influence is testable directly. Take two different secrets that answer a given
guess identically, play that guess against each, and compare:

```python
twins = [s for s in all_candidates(ruleset) if score(s, guess) == Feedback(1, 0)]
analyses = [analyse(play(secret, guess)) for secret in twins[:2]]
assert analyses[0] == analyses[1]
```

If the secret's value could reach the output at all, two games with different
secrets and identical transcripts would produce different analysis. They do not,
byte for byte. That is the claim, stated as an equality rather than as an
absence.

It is also a stronger test than the original would have been had it passed. The
substring check constrains one string in one response. This constrains the whole
function: any dependence on the secret, however indirect, breaks it.

## The general shape

The pattern is a claim about a relationship being tested as a claim about
appearance. It is easy to write because appearance is easy to check, and the
proxy is usually correlated with the property, which is exactly what makes the
gap hard to see.

The tell is that the assertion mentions a specific value rather than a
relationship. `assert "123" not in body` names a string; `assert
analyse(a) == analyse(b)` names an invariant. When a test asserts the absence of
something, it is worth asking what would have to be true for the thing to be
absent and the property still violated — and here the answer was "almost
anything".
