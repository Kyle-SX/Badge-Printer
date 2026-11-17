"""Employee badge data validation and printable sheet generation."""

import base64
import html
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    BADGE_IMAGE_FILES,
    BADGE_TYPES,
    BADGE_COUNT,
    SELECT_TYPE_PROMPT,
    ASSET_DIRECTORY,
    EMPLOYEE_BADGE_TYPE,
    EMPLOYEE_IMAGE_SIGNATURES,
    EMPLOYEE_LOGO_FILENAME,
    BADGE_WIDTH_MM,
    BADGE_HEIGHT_MM,
    BADGE_STROKE_MM,
    GUD_YELLOW,
    PAGE_WIDTH_MM,
    PAGE_HEIGHT_MM,
    LEFT_MARGIN_MM,
    TOP_MARGIN_MM,
    HORIZONTAL_GAP_MM,
    VERTICAL_GAP_MM,
)


def wrap_text(text: str, max_chars: int) -> list[str]:
    lines = []
    current_line = ""
    for word in text.split():
        candidate = f"{current_line} {word}".strip()
        if current_line and len(candidate) > max_chars:
            lines.append(current_line)
            current_line = word
        else:
            current_line = candidate
    if current_line:
        lines.append(current_line)
    return lines


@dataclass(frozen=True)
class EmployeeBadgeDetails:
    name: str
    position: str
    image_data: bytes = b""
    image_type: str = ""
    employee_number: str = ""


def _validate_employee_badges(
    selections: list[str],
    employee_badges: dict[int, EmployeeBadgeDetails],
) -> None:
    for index, selection in enumerate(selections):
        if selection != EMPLOYEE_BADGE_TYPE:
            continue
        details = employee_badges.get(index)
        if (
            details is None
            or not details.name.strip()
            or not details.position.strip()
        ):
            raise ValueError(
                f"Employee badge {index + 1} needs a name and position."
            )
        if details.image_data and details.image_type not in (
            "image/png",
            "image/jpeg",
        ):
            raise ValueError("Employee pictures must be PNG or JPEG images.")
        if details.image_data and not details.image_data.startswith(
            EMPLOYEE_IMAGE_SIGNATURES[details.image_type]
        ):
            raise ValueError("Employee picture data does not match its image type.")


def _image_data_uri(image_path: Path) -> str:
    encoded_image = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded_image}"


def _render_employee_badge(
    details: EmployeeBadgeDetails,
    x: float,
    y: float,
    employee_logo: str,
) -> str:
    if details.image_data:
        employee_image = base64.b64encode(details.image_data).decode("ascii")
        employee_image_markup = (
            f'<image x="{x}" y="{y + 4}" width="35" height="45" '
            f'href="data:{details.image_type};base64,{employee_image}" '
            'preserveAspectRatio="xMidYMid meet"/>'
        )
    else:
        employee_image_markup = (
            f'<rect x="{x}" y="{y}" width="35" height="{BADGE_HEIGHT_MM}" '
            f'fill="{GUD_YELLOW}"/>'
            f'<text x="{x + 17.5}" y="{y + BADGE_HEIGHT_MM / 2:.1f}" '
            'text-anchor="middle" dominant-baseline="middle" '
            'font-family="Arial, sans-serif" font-size="25" '
            'font-weight="bold" fill="#202020">E</text>'
        )

    escaped_name = html.escape(details.name.strip())
    escaped_employee_number = html.escape(details.employee_number.strip())
    position_lines = wrap_text(details.position.strip(), 23)
    position_text = "".join(
        f'<tspan x="{x + 60}" y="{y + 43 + (line_index - (len(position_lines) - 1) / 2) * 3.5:.2f}">'
        f"{html.escape(line)}</tspan>"
        for line_index, line in enumerate(position_lines)
    )
    employee_number_text = (
        f'<text x="{x + 60}" y="{y + 37}" text-anchor="middle" '
        'font-family="Arial, sans-serif" font-size="3.5" '
        f'font-weight="bold" fill="#514b44">NO. {escaped_employee_number}</text>'
        if escaped_employee_number
        else ""
    )
    inset = BADGE_STROKE_MM / 2
    return f"""    <g>
      <rect x="{x}" y="{y}" width="{BADGE_WIDTH_MM}" height="{BADGE_HEIGHT_MM}" fill="#ffffff"/>
      {employee_image_markup}
      <image x="{x + 36}" y="{y + 7}" width="48" height="12" href="{employee_logo}" preserveAspectRatio="xMidYMid meet"/>
      {employee_number_text}
      <text x="{x + 60}" y="{y + 29}" text-anchor="middle" font-family="Arial, sans-serif" font-size="4.5" font-weight="bold" fill="#202020">{escaped_name}</text>
      <text text-anchor="middle" font-family="Arial, sans-serif" font-size="3.5" font-weight="bold" fill="#ed7624">{position_text}</text>
      <rect x="{x + inset:.6f}" y="{y + inset:.6f}" width="{BADGE_WIDTH_MM - BADGE_STROKE_MM:.1f}" height="{BADGE_HEIGHT_MM - BADGE_STROKE_MM:.1f}" fill="none" stroke="black" stroke-width="{BADGE_STROKE_MM}"/>
    </g>"""


def _render_standard_badge(
    image_source: str,
    x: float,
    y: float,
) -> str:
    inset = BADGE_STROKE_MM / 2
    return f"""    <g>
      <image x="{x:.6f}" y="{y:.6f}" width="{BADGE_WIDTH_MM}" height="{BADGE_HEIGHT_MM}" href="{image_source}" preserveAspectRatio="none"/>
      <rect x="{x + inset:.6f}" y="{y + inset:.6f}" width="{BADGE_WIDTH_MM - BADGE_STROKE_MM:.1f}" height="{BADGE_HEIGHT_MM - BADGE_STROKE_MM:.1f}" fill="none" stroke="black" stroke-width="{BADGE_STROKE_MM}"/>
    </g>"""


def _build_print_sheet_document(badges: list[str]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Badge print sheet</title>
  <style>
    @page {{
      size: {PAGE_WIDTH_MM}mm {PAGE_HEIGHT_MM}mm;
      margin: 0;
    }}
    html, body {{
      width: {PAGE_WIDTH_MM}mm;
      height: {PAGE_HEIGHT_MM}mm;
      margin: 0;
    }}
    body {{
      padding: 0;
    }}
    @media screen {{
      body {{
        background: #e8e8e8;
      }}
      svg {{
        background: #fff;
        box-shadow: 0 2mm 8mm #888;
      }}
    }}
    svg {{
      display: block;
      width: {PAGE_WIDTH_MM}mm;
      height: {PAGE_HEIGHT_MM}mm;
    }}
  </style>
</head>
<body>
  <svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_WIDTH_MM}mm" height="{PAGE_HEIGHT_MM}mm" viewBox="0 0 {PAGE_WIDTH_MM} {PAGE_HEIGHT_MM}" aria-label="Badge print sheet">
{chr(10).join(badges)}
  </svg>
  <script>
    window.addEventListener("load", () => {{
      window.setTimeout(() => window.print(), 300);
    }});
  </script>
</body>
</html>
"""


def create_print_sheet_html(
    selections: list[str],
    image_directory: Path = ASSET_DIRECTORY,
    employee_badges: dict[int, EmployeeBadgeDetails] | None = None,
) -> str:
    if not selections or len(selections) > BADGE_COUNT:
        raise ValueError(
            f"Choose between 1 and {BADGE_COUNT} badge types."
        )
    if any(
        selection not in BADGE_TYPES and selection != SELECT_TYPE_PROMPT
        for selection in selections
    ):
        raise ValueError("Every badge must have a valid badge type.")
    if not any(selection in BADGE_TYPES for selection in selections):
        raise ValueError("Select at least one badge type.")

    employee_badges = employee_badges or {}
    _validate_employee_badges(selections, employee_badges)

    employee_logo = (
        _image_data_uri(image_directory / EMPLOYEE_LOGO_FILENAME)
        if EMPLOYEE_BADGE_TYPE in selections
        else ""
    )
    image_sources = {
        badge_type: _image_data_uri(image_directory / filename)
        for badge_type, filename in BADGE_IMAGE_FILES.items()
    }

    badges = []
    for index, selection in enumerate(selections):
        if selection == SELECT_TYPE_PROMPT:
            continue
        column = index % 2
        row = index // 2
        x = LEFT_MARGIN_MM + column * (BADGE_WIDTH_MM + HORIZONTAL_GAP_MM)
        y = TOP_MARGIN_MM + row * (BADGE_HEIGHT_MM + VERTICAL_GAP_MM)
        if selection == EMPLOYEE_BADGE_TYPE:
            badges.append(
                _render_employee_badge(
                    employee_badges[index],
                    x,
                    y,
                    employee_logo,
                )
            )
        else:
            badges.append(
                _render_standard_badge(
                    image_sources[selection],
                    x,
                    y,
                )
            )
    return _build_print_sheet_document(badges)
