# SlippageTwinAI

SlippageTwinAI builds a small empirical **execution-cost twin** from completed historical fills. It uses only features declared available when an order arrived, fits on an earlier calibration segment, skips an explicit embargo, and reports errors on untouched later fills.

```sh
./doit.sh
```

That command runs the tests, compiles every module, and measures bundled synthetic fills. It downloads nothing and needs no credentials.

## What the twin measures

The target is adverse signed slippage from arrival mid to execution price in basis points: a buy above arrival and a sell below arrival are both positive costs. The transparent ridge model uses:

- half the arrival spread in basis points;
- arrival-time volatility estimate in basis points;
- square root of declared participation rate;
- `log1p(quantity)`;
- an intercept.

The report includes coefficients, calibration bounds, calibration/test MAE, RMSE and bias, exact split timestamps, and a count of test rows outside any calibration feature bound.

## Run it

```sh
./run.sh
python -m slippagetwinai slippagetwinai/data/demo_config.json \
  slippagetwinai/data/demo_fills.csv --output report.json
```

The strict CSV header is:

```text
timestamp,side,quantity,arrival_mid,execution_price,spread_bps,volatility_bps,participation_rate
```

Searchable failures are explicit:

```text
error: no chronological holdout remains after calibration and embargo
error: timestamps must strictly increase
error: calibration matrix is singular; increase ridge or vary the data
```

## Distinction

Generic transaction-cost models often live inside execution platforms or notebooks. SlippageTwinAI is an offline, dependency-free calibration artifact with an auditable arrival-feature contract, chronological holdout, embargo, extrapolation warning, and stable JSON. It is intended for reproducible measurement and model-risk checks—not execution.

## Limitations

- The linear basis cannot capture order-book queues, nonlinear impact, latency, routing, hidden liquidity, or venue mechanics.
- Input spread, volatility and participation must truly have been knowable at arrival; this tool cannot prove upstream timestamps are honest.
- The embargo is row-count based, not clock-time based.
- Small or biased fill samples produce weak models; a deterministic fit is not a reliable forecast.
- No output is a trading recommendation or promise of future cost or profit.

## Support

Donations can fund more production and may request priority for a compatible measurement direction through the issue template with a public transaction hash. They do not guarantee implementation or buy support, ownership, returns, or preference. See [SUPPORT.md](SUPPORT.md) and verify the asset and network before sending.

Apache-2.0 licensed.
