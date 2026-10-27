"""Build the report template from its authored base and data-table recipe."""

import json
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1] / "resources/docx"


def element(parent, tag, **attributes):
    child = OxmlElement("w:" + tag)
    for key, value in attributes.items():
        child.set(qn("w:" + key), str(value))
    parent.append(child)
    return child


def main():
    recipe = json.loads((ROOT / "table-style.json").read_text(encoding="utf-8"))
    document = Document(ROOT / "template-base.docx")
    style = document.styles.add_style(recipe["name"], WD_STYLE_TYPE.TABLE)
    style.base_style = document.styles["Normal Table"]
    properties = element(style.element, "tblPr")
    margins = element(properties, "tblCellMar")
    for side in ("top", "bottom", "left", "right"):
        padding = recipe["vertical_padding_twips" if side in ("top", "bottom") else "horizontal_padding_twips"]
        element(margins, side, w=padding, type="dxa")
    borders = element(properties, "tblBorders")
    for side in ("top", "bottom", "insideH"):
        element(borders, side, val="single", sz=4, color=recipe["rule"])
    band = element(style.element, "tblStylePr", type="band1Horz")
    element(element(band, "tcPr"), "shd", fill=recipe["stripe"])
    header = element(style.element, "tblStylePr", type="firstRow")
    runs = element(header, "rPr")
    element(runs, "b")
    element(runs, "bCs")
    element(runs, "color", val="FFFFFF")
    element(element(header, "tcPr"), "shd", fill=recipe["header"])
    wrapper = document.styles["Table"].element
    rows = wrapper.find(qn("w:trPr"))
    if rows is None:
        rows = element(wrapper, "trPr")
    element(rows, "cantSplit")
    document.save(ROOT / "template.docx")
    print("Built report template with", recipe["name"])


if __name__ == "__main__":
    main()
