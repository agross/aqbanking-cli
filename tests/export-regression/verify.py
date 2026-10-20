"""Build-time regression: normal CLI export must preserve synthetic securities."""
from fractions import Fraction
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def value(node, path):
    return node.findtext(path + "/value")


with tempfile.TemporaryDirectory(prefix="finance-export-check-") as directory:
    output = Path(directory) / "context.xml"
    subprocess.run([
        "aqbanking-cli", "--noninteractive", "export",
        f"--ctxfile={Path(sys.argv[1]).resolve()}", f"--outfile={output}",
        "--exporter=xmldb", "--profile=default",
    ], check=True, capture_output=True)
    root = ET.parse(output).getroot()

securities = root.findall("./securityList/security")
require(len(securities) == 2, "Normal CLI export must retain both securities")
expected = [
    ("IE00B3RBWM25", "Synthetic A", "12345/10000", "123456/1000", "34", "56"),
    ("US0378331005", "Synthetic B", "2", "5678/100", "35", "57"),
]
for node, (isin, name, units, price, minute, second) in zip(securities, expected):
    require(value(node, "uniqueId") == isin, "ISIN changed")
    require(value(node, "nameSpace") == "ISIN", "Namespace changed")
    require(value(node, "name") == name, "Security name changed")
    require(Fraction(value(node, "units")) == Fraction(units), "Units changed")
    amount, currency = value(node, "unitPriceValue").split(":")
    require(Fraction(amount) == Fraction(price) and currency == "EUR", "Price changed")
    for path, expected_value in {
        "inUtc": "1", "date/year": "2026", "date/month": "10", "date/day": "19",
        "time/hour": "12", "time/min": minute, "time/sec": second,
    }.items():
        require(value(node.find("unitPriceDate"), path) == expected_value, "UTC timestamp changed")
require(len(root.findall("./accountInfoList/accountInfo")) == 1, "Account lost")
print("Normal CLI XMLDB export preserves synthetic securities and account")
