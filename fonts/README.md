# Fonts (optional)

Drop real font files here to have the **PDF** embed them exactly:

- `B Nazanin.ttf` (and optionally `B Nazanin Bold.ttf`) — the Persian font.
- A Times New Roman `.ttf` — the Latin font (optional; Liberation Serif is a
  metric-identical stand-in and is used automatically if Times New Roman is
  absent).

If no `B Nazanin` file is found here or on the system, the PDF falls back to a
freely-redistributable Persian font (Vazirmatn) so Persian still renders
correctly. The Word (`.docx`) file always *names* "B Nazanin" and "Times New
Roman", so on a machine that has those fonts installed, Word renders them
exactly regardless of what is in this folder.

Font files are intentionally **not committed** (see `.gitignore`) because fonts
like B Nazanin are not freely redistributable. Add them locally.
