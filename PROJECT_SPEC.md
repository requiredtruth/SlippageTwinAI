# Project specification

SlippageTwinAI fits an empirical model of signed execution cost from completed historical fills. Features are limited to values declared available at arrival: spread, volatility estimate, participation rate, and quantity. The chronological test segment is never used to fit coefficients, and an explicit row embargo separates calibration from test.

It does not recommend trades, predict returns, route or submit orders, connect to accounts, or claim that historical cost estimates will generalize.
