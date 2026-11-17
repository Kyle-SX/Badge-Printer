"""Tkinter user interface and application lifecycle."""

import base64
import tempfile
import tkinter as tk
import webbrowser
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image

from .constants import (
    BADGE_TYPES,
    SELECT_TYPE_PROMPT,
    BADGE_IMAGE_FILES,
    EMPLOYEE_BADGE_TYPE,
    EMPLOYEE_LOGO_FILENAME,
    BADGE_COUNT,
    PREVIEW_SUBSAMPLE,
    PREVIEW_WIDTH,
    PREVIEW_HEIGHT,
    ASSET_DIRECTORY,
    GUD_YELLOW,
    GUD_ORANGE,
    GUD_RED,
    APP_BACKGROUND,
    CARD_BACKGROUND,
    PREVIEW_BACKGROUND,
    BRAND_PALE_YELLOW,
    BRAND_HOVER_YELLOW,
    BRAND_BORDER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_ACCENT,
)
from .print_sheet import EmployeeBadgeDetails, create_print_sheet_html


def change_badge_type_with_wheel(
    event: tk.Event,
    choice: tk.StringVar,
    direction: int | None = None,
) -> str:
    if direction is None:
        direction = -1 if event.delta > 0 else 1
    current_type = choice.get()
    if current_type in BADGE_TYPES:
        current_index = BADGE_TYPES.index(current_type)
        next_index = max(
            0,
            min(len(BADGE_TYPES) - 1, current_index + direction),
        )
    else:
        next_index = 0
    choice.set(BADGE_TYPES[next_index])
    return "break"


class BadgePrinter:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.ready = False
        root.title("BADGE PRINTER")
        root.geometry("1040x900")
        root.minsize(900, 760)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.print_directory: tempfile.TemporaryDirectory[str] | None = None
        self.configure_styles()

        self.preview_images: dict[str, tk.PhotoImage] = {}
        for badge_type, filename in BADGE_IMAGE_FILES.items():
            image_path = ASSET_DIRECTORY / filename
            try:
                source_image = tk.PhotoImage(master=root, file=str(image_path))
            except (OSError, tk.TclError) as error:
                messagebox.showerror(
                    "Could not load badge image",
                    f"Could not load the {badge_type} preview:\n"
                    f"{image_path}\n\n{error}",
                    parent=root,
                )
                self.preview_images.clear()
                return
            self.preview_images[badge_type] = source_image.subsample(
                PREVIEW_SUBSAMPLE,
                PREVIEW_SUBSAMPLE,
            )

        logo_path = ASSET_DIRECTORY / EMPLOYEE_LOGO_FILENAME
        try:
            logo_source = tk.PhotoImage(master=root, file=str(logo_path))
        except (OSError, tk.TclError) as error:
            messagebox.showerror(
                "Could not load badge logo",
                f"Could not load the Employee badge logo:\n"
                f"{logo_path}\n\n{error}",
                parent=root,
            )
            self.preview_images.clear()
            return
        self.employee_logo_preview = logo_source.subsample(7, 7)

        self.employee_names = [
            tk.StringVar(master=root) for _ in range(BADGE_COUNT)
        ]
        self.employee_numbers = [
            tk.StringVar(master=root) for _ in range(BADGE_COUNT)
        ]
        self.employee_positions = [
            tk.StringVar(master=root) for _ in range(BADGE_COUNT)
        ]
        self.employee_photo_paths: list[Path | None] = [
            None for _ in range(BADGE_COUNT)
        ]
        self.employee_photo_images: list[tk.PhotoImage | None] = [
            None for _ in range(BADGE_COUNT)
        ]
        self.employee_preview_images: list[tk.PhotoImage | None] = [
            None for _ in range(BADGE_COUNT)
        ]
        self.employee_photo_buttons: list[ttk.Button] = []
        self.badge_previews: list[tk.Canvas] = []

        frame = ttk.Frame(root, style="App.TFrame", padding=(28, 24))
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        header = ttk.Frame(frame, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        title_group = ttk.Frame(header, style="App.TFrame")
        title_group.grid(row=0, column=0, sticky="w")
        ttk.Label(
            title_group,
            text="BADGE PRINTER",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")
        logo_source = tk.PhotoImage(
            master=root,
            file=str(ASSET_DIRECTORY / "LOGO (3).png"),
        )
        self.logo_image = tk.PhotoImage(master=root, width=51, height=33)
        for y in range(33):
            source_y = min((y * logo_source.height()) // 33, logo_source.height() - 1)
            row = []
            for x in range(51):
                source_x = min((x * logo_source.width()) // 51, logo_source.width() - 1)
                red, green, blue = logo_source.get(source_x, source_y)
                row.append(f"#{red:02x}{green:02x}{blue:02x}")
            self.logo_image.put("{" + " ".join(row) + "}", to=(0, y))
        corner_radius = 4
        for y in range(corner_radius):
            for x in range(corner_radius):
                if (corner_radius - x - 0.5) ** 2 + (
                    corner_radius - y - 0.5
                ) ** 2 > corner_radius**2:
                    for corner_x, corner_y in (
                        (x, y),
                        (self.logo_image.width() - 1 - x, y),
                        (x, self.logo_image.height() - 1 - y),
                        (
                            self.logo_image.width() - 1 - x,
                            self.logo_image.height() - 1 - y,
                        ),
                    ):
                        self.logo_image.transparency_set(corner_x, corner_y, True)
        ttk.Label(
            title_group,
            image=self.logo_image,
            style="App.TLabel",
        ).grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Label(
            header,
            text=(
                "Choose each badge type; Employee badges need a name and "
                "position. Photos are optional."
            ),
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        brand_mark = tk.Canvas(
            header,
            width=78,
            height=6,
            background=APP_BACKGROUND,
            highlightthickness=0,
            borderwidth=0,
        )
        brand_mark.grid(row=2, column=0, sticky="w", pady=(9, 0))
        brand_mark.create_rectangle(0, 0, 26, 6, fill=GUD_YELLOW, outline="")
        brand_mark.create_rectangle(26, 0, 52, 6, fill=GUD_ORANGE, outline="")
        brand_mark.create_rectangle(52, 0, 78, 6, fill=GUD_RED, outline="")
        self.count_label = ttk.Label(
            header,
            text=f"0 / {BADGE_COUNT} selected",
            style="Count.TLabel",
        )
        self.count_label.grid(row=0, column=1, rowspan=2, sticky="e", padx=(16, 0))

        cards_area = ttk.Frame(frame, style="App.TFrame")
        cards_area.grid(row=1, column=0, sticky="nsew")
        cards_area.columnconfigure(0, weight=1)
        cards_area.rowconfigure(0, weight=1)
        cards_canvas = tk.Canvas(
            cards_area,
            background=APP_BACKGROUND,
            highlightthickness=0,
            borderwidth=0,
        )
        cards_canvas.grid(row=0, column=0, sticky="nsew")
        cards_scrollbar = ttk.Scrollbar(
            cards_area,
            orient="vertical",
            command=cards_canvas.yview,
        )
        cards_scrollbar.grid(row=0, column=1, sticky="ns")
        cards_canvas.configure(yscrollcommand=cards_scrollbar.set)
        cards_frame = ttk.Frame(cards_canvas, style="App.TFrame")
        cards_window = cards_canvas.create_window(
            (0, 0),
            window=cards_frame,
            anchor="nw",
        )
        cards_frame.columnconfigure(0, weight=1, uniform="badge_columns")
        cards_frame.columnconfigure(1, weight=1, uniform="badge_columns")
        cards_canvas.bind(
            "<Configure>",
            lambda event: cards_canvas.itemconfigure(
                cards_window,
                width=event.width,
            ),
        )
        cards_frame.bind(
            "<Configure>",
            lambda event: cards_canvas.configure(
                scrollregion=(0, 0, event.width, event.height)
            ),
        )

        self.selections: list[tk.StringVar] = []
        for index in range(BADGE_COUNT):
            row = index // 2
            column = index % 2
            card = ttk.Frame(cards_frame, style="Card.TFrame", padding=12)
            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=6,
                pady=4,
            )
            cards_frame.rowconfigure(row, weight=1, uniform="badge_rows")
            card.columnconfigure(0, weight=1)
            ttk.Label(
                card,
                text=f"BADGE {index + 1:02}",
                style="CardTitle.TLabel",
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))

            selection = tk.StringVar(value=SELECT_TYPE_PROMPT)
            badge_type_dropdown = ttk.Combobox(
                card,
                textvariable=selection,
                values=BADGE_TYPES,
                state="readonly",
                style="Badge.TCombobox",
            )
            badge_type_dropdown.grid(
                row=1,
                column=0,
                sticky="ew",
                padx=(0, 12),
            )
            badge_type_dropdown.bind(
                "<MouseWheel>",
                lambda event, choice=selection: change_badge_type_with_wheel(
                    event,
                    choice,
                ),
            )
            badge_type_dropdown.bind(
                "<Button-4>",
                lambda event, choice=selection: change_badge_type_with_wheel(
                    event,
                    choice,
                    -1,
                ),
            )
            badge_type_dropdown.bind(
                "<Button-5>",
                lambda event, choice=selection: change_badge_type_with_wheel(
                    event,
                    choice,
                    1,
                ),
            )
            preview = tk.Canvas(
                card,
                width=PREVIEW_WIDTH,
                height=PREVIEW_HEIGHT,
                background=PREVIEW_BACKGROUND,
                highlightthickness=1,
                highlightbackground=BRAND_BORDER,
                borderwidth=0,
            )
            preview.grid(
                row=0,
                column=1,
                rowspan=2,
                sticky="e",
                padx=(12, 0),
            )
            self.badge_previews.append(preview)
            selection.trace_add(
                "write",
                lambda *_, choice=selection, display=preview,
                badge_index=index: self.update_preview(
                    choice,
                    display,
                    badge_index,
                ),
            )
            self.selections.append(selection)
            employee_fields = ttk.Frame(card, style="Card.TFrame")
            employee_fields.grid(
                row=2,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(8, 0),
            )
            employee_fields.columnconfigure(1, weight=1)
            ttk.Label(
                employee_fields,
                text="Name",
                style="CardTitle.TLabel",
            ).grid(row=0, column=0, sticky="w", padx=(0, 6))
            name_entry = ttk.Entry(
                employee_fields,
                textvariable=self.employee_names[index],
                font=("Segoe UI", 9),
            )
            name_entry.grid(row=0, column=1, columnspan=2, sticky="ew")
            ttk.Label(
                employee_fields,
                text="Employee No.",
                style="CardTitle.TLabel",
            ).grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
            employee_number_entry = ttk.Entry(
                employee_fields,
                textvariable=self.employee_numbers[index],
                font=("Segoe UI", 9),
            )
            employee_number_entry.grid(
                row=1,
                column=1,
                columnspan=2,
                sticky="ew",
                pady=(6, 0),
            )
            ttk.Label(
                employee_fields,
                text="Position",
                style="CardTitle.TLabel",
            ).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
            position_entry = ttk.Entry(
                employee_fields,
                textvariable=self.employee_positions[index],
                font=("Segoe UI", 9),
            )
            position_entry.grid(
                row=2,
                column=1,
                sticky="ew",
                padx=(0, 8),
                pady=(6, 0),
            )
            photo_button = ttk.Button(
                employee_fields,
                text="Add photo",
                command=lambda badge_index=index: self.choose_employee_photo(
                    badge_index
                ),
                style="Secondary.TButton",
            )
            photo_button.grid(row=2, column=2, sticky="e", pady=(6, 0))
            self.employee_photo_buttons.append(photo_button)
            ttk.Label(
                employee_fields,
                text="Supported photo files: PNG, JPG, JPEG",
                style="PhotoHint.TLabel",
            ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 0))
            employee_fields.grid_remove()
            selection.trace_add(
                "write",
                lambda *_, choice=selection, fields=employee_fields,
                badge_index=index: self.update_badge_details_visibility(
                    choice,
                    fields,
                    badge_index,
                ),
            )
            self.employee_names[index].trace_add(
                "write",
                lambda *_, choice=selection, display=preview,
                badge_index=index: self.update_preview(
                    choice,
                    display,
                    badge_index,
                ),
            )
            self.employee_positions[index].trace_add(
                "write",
                lambda *_, choice=selection, display=preview,
                badge_index=index: self.update_preview(
                    choice,
                    display,
                    badge_index,
                ),
            )
            self.employee_numbers[index].trace_add(
                "write",
                lambda *_, choice=selection, display=preview,
                badge_index=index: self.update_preview(
                    choice,
                    display,
                    badge_index,
                ),
            )

        actions = ttk.Frame(frame, style="App.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        actions.columnconfigure(3, weight=1)
        ttk.Button(
            actions,
            text="🖊 Auto fill",
            command=self.fill_test_options,
            style="Secondary.TButton",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Button(
            actions,
            text="50/50 fill",
            command=self.open_half_fill_menu,
            style="Secondary.TButton",
        ).grid(row=0, column=1, sticky="w", padx=(0, 10))
        ttk.Button(
            actions,
            text="1 type fill",
            command=self.open_single_fill_menu,
            style="Secondary.TButton",
        ).grid(row=0, column=2, sticky="w", padx=(0, 10))
        ttk.Button(
            actions,
            text="Clear all",
            command=self.clear_all,
            style="Secondary.TButton",
        ).grid(row=0, column=3, sticky="w")
        self.print_button = ttk.Button(
            actions,
            text="🖨 Print badges",
            command=self.print_badges,
            style="Primary.TButton",
            state="disabled",
        )
        self.print_button.grid(row=0, column=4, sticky="e")
        self.status_label = ttk.Label(
            frame,
            text="Choose at least one badge type to enable printing.",
            style="Status.TLabel",
            wraplength=850,
        )
        self.status_label.grid(
            row=3,
            column=0,
            sticky="w",
            pady=(12, 0),
        )
        self.ready = True

    def configure_styles(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        self.root.configure(background=APP_BACKGROUND)
        style.configure("App.TFrame", background=APP_BACKGROUND)
        style.configure("App.TLabel", background=APP_BACKGROUND)
        style.configure(
            "Card.TFrame",
            background=CARD_BACKGROUND,
            bordercolor=BRAND_BORDER,
            relief="solid",
            borderwidth=1,
        )
        style.configure(
            "Title.TLabel",
            background=APP_BACKGROUND,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 23, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=APP_BACKGROUND,
            foreground=TEXT_SECONDARY,
            font=("Segoe UI", 10),
        )
        style.configure(
            "PhotoHint.TLabel",
            background=CARD_BACKGROUND,
            foreground=TEXT_SECONDARY,
            font=("Segoe UI", 8),
        )
        style.configure(
            "Count.TLabel",
            background=GUD_YELLOW,
            foreground=TEXT_ACCENT,
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
        )
        style.configure(
            "CardTitle.TLabel",
            background=CARD_BACKGROUND,
            foreground=TEXT_PRIMARY,
            font=("Segoe UI", 9, "bold"),
        )
        style.configure(
            "Preview.TLabel",
            background=PREVIEW_BACKGROUND,
            foreground=TEXT_SECONDARY,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Badge.TCombobox",
            fieldbackground=CARD_BACKGROUND,
            background=CARD_BACKGROUND,
            foreground=TEXT_PRIMARY,
            padding=7,
        )
        style.configure(
            "Status.TLabel",
            background=APP_BACKGROUND,
            foreground=TEXT_SECONDARY,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Primary.TButton",
            background=GUD_ORANGE,
            foreground="#ffffff",
            font=("Segoe UI", 10, "bold"),
            padding=(22, 11),
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[
                ("disabled", "#c9c1b2"),
                ("active", GUD_RED),
                ("!disabled", GUD_ORANGE),
            ],
            foreground=[("disabled", "#f7f4ed"), ("!disabled", "#ffffff")],
        )
        style.configure(
            "Secondary.TButton",
            background=BRAND_PALE_YELLOW,
            foreground=TEXT_ACCENT,
            font=("Segoe UI", 9, "bold"),
            padding=(14, 10),
            borderwidth=0,
        )
        style.map(
            "Secondary.TButton",
            background=[
                ("active", BRAND_HOVER_YELLOW),
                ("!disabled", BRAND_PALE_YELLOW),
            ],
        )

    def update_preview(
        self,
        selection: tk.StringVar,
        preview: tk.Canvas,
        badge_index: int,
    ) -> None:
        badge_type = selection.get()
        preview.delete("all")
        if badge_type in self.preview_images:
            preview.create_image(
                PREVIEW_WIDTH / 2,
                PREVIEW_HEIGHT / 2,
                image=self.preview_images[badge_type],
                anchor="center",
                tags=("badge-image",),
            )
        elif badge_type == EMPLOYEE_BADGE_TYPE:
            employee_photo = self.employee_photo_images[badge_index]
            if employee_photo is not None:
                subsample = max(
                    1,
                    (employee_photo.width() + 69) // 70,
                    (employee_photo.height() + 89) // 90,
                )
                self.employee_preview_images[badge_index] = employee_photo.subsample(
                    subsample,
                    subsample,
                )
                preview.create_image(
                    37,
                    PREVIEW_HEIGHT / 2,
                    image=self.employee_preview_images[badge_index],
                    anchor="center",
                    tags=("badge-image",),
                )
            else:
                preview.create_rectangle(
                    0,
                    0,
                    74,
                    PREVIEW_HEIGHT,
                    fill=GUD_YELLOW,
                    outline="",
                )
                preview.create_text(
                    37,
                    58,
                    text="E",
                    anchor="center",
                    fill=TEXT_PRIMARY,
                    font=("Segoe UI", 44, "bold"),
                )
            preview.create_image(
                124,
                31,
                image=self.employee_logo_preview,
                anchor="center",
            )
            preview.create_text(
                124,
                83,
                text=(
                    f"NO. {self.employee_numbers[badge_index].get()}"
                    if self.employee_numbers[badge_index].get().strip()
                    else ""
                ),
                fill=TEXT_SECONDARY,
                font=("Segoe UI", 8, "bold"),
                width=100,
                justify="center",
            )
            preview.create_text(
                124,
                66,
                text=self.employee_names[badge_index].get(),
                fill=TEXT_PRIMARY,
                font=("Segoe UI", 9, "bold"),
                width=100,
                justify="center",
            )
            preview.create_text(
                124,
                94,
                text=self.employee_positions[badge_index].get(),
                fill=GUD_ORANGE,
                font=("Segoe UI", 8, "bold"),
                width=100,
                justify="center",
            )
        self.update_selection_count()

    def update_badge_details_visibility(
        self,
        selection: tk.StringVar,
        fields: ttk.Frame,
        badge_index: int,
    ) -> None:
        if selection.get() == EMPLOYEE_BADGE_TYPE:
            fields.grid()
        else:
            fields.grid_remove()
        self.update_preview(selection, self.badge_previews[badge_index], badge_index)

    def update_selection_count(self) -> None:
        selected_count = sum(
            selection.get() in BADGE_TYPES for selection in self.selections
        )
        self.count_label.configure(
            text=f"{selected_count} / {BADGE_COUNT} selected"
        )
        employee_details_complete = all(
            selection.get() != EMPLOYEE_BADGE_TYPE
            or (
                bool(self.employee_names[index].get().strip())
                and bool(self.employee_positions[index].get().strip())
            )
            for index, selection in enumerate(self.selections)
        )
        can_print = selected_count > 0 and employee_details_complete
        self.print_button.configure(
            state="normal" if can_print else "disabled"
        )
        if selected_count == 0:
            status = "Choose at least one badge type to enable printing."
        elif not employee_details_complete:
            status = "Add a name and position for each Employee badge."
        else:
            badge_word = "badge" if selected_count == 1 else "badges"
            status = f"Ready to print {selected_count} {badge_word}."
        self.status_label.configure(text=status)

    def choose_employee_photo(self, badge_index: int) -> None:
        image_path = filedialog.askopenfilename(
            parent=self.root,
            title="Choose employee photo",
            filetypes=(
                ("Image files", "*.png *.jpg *.jpeg"),
                ("JPEG images", "*.jpg *.jpeg"),
                ("PNG images", "*.png"),
            ),
        )
        if not image_path:
            return

        path = Path(image_path)
        try:
            with Image.open(path) as source_image:
                image_format = source_image.format
                if image_format not in ("PNG", "JPEG"):
                    raise ValueError("Only PNG and JPEG images are supported.")
                if image_format == "JPEG":
                    source_image.thumbnail((70, 90))
                    preview_image = source_image.convert("RGB")
                    image_buffer = BytesIO()
                    preview_image.save(image_buffer, format="PNG")
                    image = tk.PhotoImage(
                        master=self.root,
                        data=base64.b64encode(
                            image_buffer.getvalue()
                        ).decode("ascii"),
                    )
                else:
                    image = tk.PhotoImage(master=self.root, file=str(path))
        except (OSError, tk.TclError, ValueError) as error:
            messagebox.showerror(
                "Could not load employee photo",
                f"Choose a valid PNG or JPEG image:\n{path}\n\n{error}",
                parent=self.root,
            )
            return

        self.employee_photo_paths[badge_index] = path
        self.employee_photo_images[badge_index] = image
        self.employee_photo_buttons[badge_index].configure(
            text=path.name if len(path.name) <= 16 else "Change photo"
        )
        self.update_preview(
            self.selections[badge_index],
            self.badge_previews[badge_index],
            badge_index,
        )

    def print_badges(self) -> None:
        selections = [selection.get() for selection in self.selections]
        if not any(selection in BADGE_TYPES for selection in selections):
            messagebox.showwarning(
                "No badges selected",
                "Select at least one badge type before printing.",
                parent=self.root,
            )
            return

        employee_badges = {}
        for index, selection in enumerate(selections):
            if selection != EMPLOYEE_BADGE_TYPE:
                continue
            image_path = self.employee_photo_paths[index]
            name = self.employee_names[index].get().strip()
            position = self.employee_positions[index].get().strip()
            employee_number = self.employee_numbers[index].get().strip()
            if not name or not position:
                messagebox.showwarning(
                    "Missing employee details",
                    f"Add a name and position for Employee badge {index + 1}.",
                    parent=self.root,
                )
                return
            image_data = b""
            image_type = ""
            if image_path is not None:
                try:
                    image_data = image_path.read_bytes()
                except OSError as error:
                    messagebox.showerror(
                        "Could not read employee photo",
                        f"The selected photo could not be read:\n{image_path}\n\n{error}",
                        parent=self.root,
                    )
                    return
                if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
                    image_type = "image/png"
                elif image_data.startswith(b"\xff\xd8\xff"):
                    image_type = "image/jpeg"
                else:
                    messagebox.showerror(
                        "Unsupported employee photo",
                        "Employee photos must be PNG or JPEG images.",
                        parent=self.root,
                    )
                    return
            employee_badges[index] = EmployeeBadgeDetails(
                name=name,
                position=position,
                image_data=image_data,
                image_type=image_type,
                employee_number=employee_number,
            )

        try:
            if self.print_directory is None:
                self.print_directory = tempfile.TemporaryDirectory(
                    prefix="badge-print-"
                )
            print_path = Path(self.print_directory.name) / "badge_print_sheet.html"
            print_path.write_text(
                create_print_sheet_html(selections, employee_badges=employee_badges),
                encoding="utf-8",
            )
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Could not save print sheet",
                f"The temporary print sheet could not be prepared:\n{error}",
                parent=self.root,
            )
            return

        sheet_uri = print_path.resolve().as_uri()
        if webbrowser.open(sheet_uri):
            self.status_label.configure(
                text=(
                    "Print sheet opened in your browser; its print dialog "
                    "should appear automatically. If it does not, press "
                    "Ctrl+P. Select the printer and custom 217 × 279 mm "
                    "paper, use 100% / actual size, set margins to none, "
                    "and turn off browser headers and footers."
                )
            )
        else:
            messagebox.showerror(
                "Could not open print dialog",
                "The print sheet was prepared, but the browser could not be "
                "opened automatically. Check that a default browser is set.",
                parent=self.root,
            )

    def fill_test_options(self) -> None:
        standard_badge_types = tuple(BADGE_IMAGE_FILES)
        for index, selection in enumerate(self.selections):
            selection.set(standard_badge_types[index % len(standard_badge_types)])

    def clear_all(self) -> None:
        for index, selection in enumerate(self.selections):
            selection.set("")
            self.employee_names[index].set("")
            self.employee_numbers[index].set("")
            self.employee_positions[index].set("")
            self.employee_photo_paths[index] = None
            self.employee_photo_images[index] = None
            self.employee_preview_images[index] = None
            self.employee_photo_buttons[index].configure(text="Add photo")

    def open_single_fill_menu(self) -> None:
        menu = tk.Toplevel(self.root)
        menu.title("1 type fill")
        menu.transient(self.root)
        menu.resizable(False, False)

        content = ttk.Frame(menu, style="App.TFrame", padding=20)
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        ttk.Label(
            content,
            text="Choose the badge type to use for all eight badges.",
            style="Subtitle.TLabel",
            wraplength=320,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        choice = tk.StringVar(master=menu, value=SELECT_TYPE_PROMPT)
        ttk.Label(
            content,
            text="Badge type",
            style="App.TLabel",
        ).grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        ttk.Combobox(
            content,
            textvariable=choice,
            values=(SELECT_TYPE_PROMPT, *BADGE_TYPES),
            state="readonly",
            style="Badge.TCombobox",
        ).grid(row=1, column=1, sticky="ew", pady=5)

        buttons = ttk.Frame(content, style="App.TFrame")
        buttons.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        apply_button = ttk.Button(
            buttons,
            text="Apply",
            style="Primary.TButton",
            state="disabled",
        )
        apply_button.pack(side="right")
        ttk.Button(
            buttons,
            text="Cancel",
            style="Secondary.TButton",
            command=menu.destroy,
        ).pack(side="right", padx=(0, 8))

        def update_apply_state(*_: str) -> None:
            apply_button.configure(
                state="normal" if choice.get() in BADGE_TYPES else "disabled"
            )

        def apply_choice() -> None:
            for selection in self.selections:
                selection.set(choice.get())
            menu.destroy()

        choice.trace_add("write", update_apply_state)
        apply_button.configure(command=apply_choice)
        menu.protocol("WM_DELETE_WINDOW", menu.destroy)
        menu.grab_set()
        menu.focus_set()

    def open_half_fill_menu(self) -> None:
        menu = tk.Toplevel(self.root)
        menu.title("50/50 fill")
        menu.transient(self.root)
        menu.resizable(False, False)

        content = ttk.Frame(menu, style="App.TFrame", padding=20)
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        ttk.Label(
            content,
            text="Choose two different badge types. Each fills four badges.",
            style="Subtitle.TLabel",
            wraplength=320,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        first_choice = tk.StringVar(master=menu, value=SELECT_TYPE_PROMPT)
        second_choice = tk.StringVar(master=menu, value=SELECT_TYPE_PROMPT)
        for row, label, choice in (
            (1, "First type", first_choice),
            (2, "Second type", second_choice),
        ):
            ttk.Label(
                content,
                text=label,
                style="App.TLabel",
            ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            ttk.Combobox(
                content,
                textvariable=choice,
                values=(SELECT_TYPE_PROMPT, *BADGE_TYPES),
                state="readonly",
                style="Badge.TCombobox",
            ).grid(row=row, column=1, sticky="ew", pady=5)

        buttons = ttk.Frame(content, style="App.TFrame")
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        apply_button = ttk.Button(
            buttons,
            text="Apply",
            style="Primary.TButton",
            state="disabled",
        )
        apply_button.pack(side="right")
        ttk.Button(
            buttons,
            text="Cancel",
            style="Secondary.TButton",
            command=menu.destroy,
        ).pack(side="right", padx=(0, 8))

        def update_apply_state(*_: str) -> None:
            valid_choices = (
                first_choice.get() in BADGE_TYPES
                and second_choice.get() in BADGE_TYPES
                and first_choice.get() != second_choice.get()
            )
            apply_button.configure(state="normal" if valid_choices else "disabled")

        def apply_choices() -> None:
            half_count = BADGE_COUNT // 2
            for index, selection in enumerate(self.selections):
                selection.set(
                    first_choice.get() if index < half_count else second_choice.get()
                )
            menu.destroy()

        first_choice.trace_add("write", update_apply_state)
        second_choice.trace_add("write", update_apply_state)
        apply_button.configure(command=apply_choices)
        menu.protocol("WM_DELETE_WINDOW", menu.destroy)
        menu.grab_set()
        menu.focus_set()

    def close(self) -> None:
        if self.print_directory is not None:
            self.print_directory.cleanup()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = BadgePrinter(root)
    if app.ready:
        root.mainloop()
    else:
        root.destroy()
