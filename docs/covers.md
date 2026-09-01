# Cover guide

Scriber calculates cover geometry only after print pagination stabilizes. Changing the manuscript can change the gutter band, page count, spine width, and final wrap width.

## Generate the guide

```bash
scriber cover-template <slug>
```

The generated PNG in `dist/cover/` uses the configured output DPI and shows:

- red trim boundaries;
- blue spine folds;
- green safe areas;
- full bleed;
- the reserved back-cover barcode region.

The template is regenerated during every normal build.

## Prepare panel artwork

Save:

```text
assets/cover/front.png
assets/cover/back.png
```

Each source panel covers one trim panel, its outer bleed, and the top and bottom bleed. Match the guide's panel aspect ratio and target pixel dimensions to avoid cropping or upscaling.

The default `enabled = "auto"` compiles a cover when both files exist. It does nothing when neither exists. If only one exists, add the other before expecting cover output.

## Resolution

The default profile uses 300 DPI. Scriber calculates effective DPI from source pixels and physical panel size. Draft builds warn when either dimension is too small. Release builds treat that condition as an error.

Do not enlarge a low-resolution image merely by changing its DPI metadata. The actual pixel dimensions determine print quality.

## Compiled files

A cover build creates:

- `<slug>_paperback_cover.pdf`: single-page full wrap for paperback upload;
- `<slug>_paperback_cover_preview.jpg`: reduced review image;
- `<slug>_ebook_cover.jpg`: 1600 × 2560 ebook cover generated from the front panel;
- `<slug>_cover_template.png`: current geometry guide.

Spine title and author text are generated only when the active profile permits spine text and the computed spine has enough pixels.

## Color and text

Scriber preserves RGB cover artwork and produces an RGB print PDF. Confirm the retailer's current color-space requirements and inspect the uploaded cover in its previewer.

Keep titles, author names, logos, and faces within safe areas. Bleed should contain background artwork only. Leave the barcode reservation clear unless the final artwork intentionally includes a valid owned barcode.

## Rebuild triggers

Regenerate and redesign against the template after changing:

- manuscript length;
- trim width or height;
- paper color or stock;
- ink mode;
- publishing profile;
- bleed or DPI settings.

Never reuse a wrap generated for a different page count.
