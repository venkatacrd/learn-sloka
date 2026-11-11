# Gold text

Hand-checked, correct text for a few pages of the reference PDF (`01_Chapter_Sanskrit.pdf`, see Q1a/Q1b in
`specs/open-questions.md`). Tests compare the extractor's output against these files, so a typo here counts
as a tool error.

## Files

One file per page, named by page number (1-based):

```
01_Chapter_Sanskrit_p1.txt
01_Chapter_Sanskrit_p4.txt
```

Pick 2–3 pages: ideally one with the chapter heading, one with only verses, and one with the colophon.

## Format

- Plain text, UTF-8, Unicode Devanagari (NFC). Do **not** copy-paste from the PDF: its font (Sanskrit99) is
  not Unicode and pastes as Latin gibberish.
- One line per printed line; one blank line between units (heading, verse, colophon).
- Keep exactly as printed: dandas `।` `॥`, verse numbers in the same digits (`॥ १ ॥`), avagraha `ऽ`,
  heading and colophon lines.
- Leave out: page numbers, running headers/footers, and any non-Sanskrit (English) text.
- No trailing spaces; file ends with a single newline.

## About the reference PDF

`01_Chapter_Sanskrit.pdf` is **Bhagavad Gita, chapter 1 (Arjuna-viṣāda-yoga), verses 1–47**, 4 pages,
made in Word 2013 with the Sanskrit99 font. The only non-Sanskrit text is the page number (Cambria).

- Layout is **two columns**; write column 1 top to bottom, then column 2.
- Each printed line holds one half-verse with a wide gap in the middle; write that gap as **one space**.
- Leave out the running header (`॥ श्रीमद्भगवद्गीता ॥` / `१॥ अर्जुनविषादयोगः ॥`) and the page number.
- Keep the invocation `॥ ॐ श्री परमात्मने नमः ॥`, `॥ अथ प्रथमोऽध्यायः ॥`, the title, speaker lines
  (`धृतराष्ट्र उवाच -`) and the closing colophon (`॥ ॐ तत्सदिति … ॥`), each as its own unit.
- Use pages **p1** (headings, speaker lines, verses 1–11) and **p4** (verses 38–47 and the colophon).
  Skip p2 and p3: verses 21 and 28 are split by a speaker line, which the tool outputs after the verse
  (spec FR-EX-09), so a page compared in printed order would not match.
- The text is widely available online in Unicode; editions differ in spacing and sandhi, so proofread
  against the PDF.

## Example (start of p1)

```
॥ ॐ श्री परमात्मने नमः ॥

॥ अथ प्रथमोऽध्यायः ॥

अर्जुनविषादयोगः

धृतराष्ट्र उवाच -

धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः ।
मामकाः पाण्डवाश्चैव किमकुर्वत सञ्जय ॥ १ ॥
```

## How to produce it

- If the text is well known, copy it from a trusted Unicode source, then proofread line by line against the
  PDF (editions differ).
- Otherwise type it with the macOS "Devanagari – QWERTY" keyboard
  (System Settings → Keyboard → Input Sources).
