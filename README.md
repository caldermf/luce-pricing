# luce-pricing
Using the Luce model to estimate fair prices for place and show bets in horse racing.

## The Luce model for horse racing
This is a toy project inspired by the paper [Enumerative Theory for the Tsetlin Library](https://arxiv.org/pdf/2306.16521) by Chatterjee, Diaconis, and Kim. In it, they consider "weighted sampling without replacement from an urn". This describes a probability distribution on permutations of objects in the urn. The idea, discussed in their Section 2.2.6, is to apply this in practice to horse racing as follows.

Bettors at the racetrack can ordinarily place three types of bets on these horses: to win, to place (2nd place or better) or to show (3rd place or better). The underlying assumption which we hope to exploit is that the "win" market is extremely efficient (bettors are very good at figuring out which horses will win) while the place and show markets are less so.

The goal of this tool is to concretely implement this: to run the Luce model on weights given by actual data scraped from "win" bets on actual races, and to then search for inefficiencies in the corresponding "show" market.
# horse-betting
