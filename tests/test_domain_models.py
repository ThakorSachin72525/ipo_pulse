from datetime import date

from app.models.ipo_model import GMPObservation, IPO, PredictionRecord


def test_expected_listing_price_and_profit_calculation():
    ipo = IPO(
        id="IP-001",
        name="Demo IPO",
        issue_price=100.0,
        lot_size=100,
        listing_date=date(2026, 9, 25),
    )

    gmp = GMPObservation(
        ipo_id=ipo.id,
        date=date(2026, 9, 24),
        gmp=25.0,
        gmp_percent=25.0,
        source="ipo_guru",
    )

    prediction = PredictionRecord.from_gmp(ipo=ipo, gmp_observation=gmp)

    assert prediction.expected_listing_price == 125.0
    assert prediction.expected_profit == 2500.0
    assert prediction.expected_return == 25.0


def test_prediction_record_tracks_values_without_mutating_gmp_history():
    ipo = IPO(
        id="IP-002",
        name="Another Demo IPO",
        issue_price=80.0,
        lot_size=250,
        listing_date=date(2026, 9, 27),
    )

    gmp_one = GMPObservation(
        ipo_id=ipo.id,
        date=date(2026, 9, 26),
        gmp=20.0,
        gmp_percent=25.0,
        source="ipo_guru",
    )

    prediction = PredictionRecord.from_gmp(ipo=ipo, gmp_observation=gmp_one)

    assert prediction.gmp_value == 20.0
    assert prediction.expected_listing_price == 100.0
    assert gmp_one.gmp == 20.0
    assert prediction.expected_profit == 5000.0
