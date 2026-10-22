import pandas as pd

from parse import clean_description, finalize, parse_files


def test_clean_description_strips_markup():
    raw = "[b]Bold[/b] &amp;mdash; see [url=https://x.com]the rules[/url] at https://x.com/faq&#10;&#10;End"
    assert clean_description(raw) == "Bold — see the rules at End"


def test_clean_description_empty():
    assert clean_description(None) == ""
    assert clean_description("   ") == ""


def test_parse_fixture(sample_xml):
    df = finalize(parse_files([sample_xml]))
    assert df["id"].tolist() == [13]  # unranked game and expansion dropped
    row = df.iloc[0]
    assert row["name"] == "CATAN"
    assert row["year"] == 1995
    assert row["rank"] == 520
    assert row["best_players"] == 4  # "4+" bucket ignored
    assert row["weight"] == 2.29
    assert row["owned"] == 230000
    assert list(row["mechanics"]) == ["Dice Rolling", "Trading"]
    assert list(row["designers"]) == ["Klaus Teuber"]
    assert "[i]" not in row["description"] and "http" not in row["description"]
    assert "—" in row["description"]
    assert row["embed_text"].startswith("CATAN. In CATAN (formerly The Settlers of Catan)")
    assert not row["short_desc"]


def test_zero_means_unknown(sample_xml):
    df = parse_files([sample_xml]).set_index("id")
    assert pd.isna(df.loc[999999, "year"])
    assert pd.isna(df.loc[999999, "weight"])
