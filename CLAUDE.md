# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Cure Dolly Textbook** - a Japanese language learning resource based on the Cure Dolly YouTube grammar course. It is a static HTML resource, not a software project.

## Structure

```
Kurodo/
├── index.html          (intro + navigation to all lessons)
├── onomatopoeia.html   (onomatopoeia reference page)
├── styles.css          (shared CSS for lesson pages)
├── lessons/            (88 individual lesson files)
│   ├── lesson-01.html
│   ├── lesson-02.html
│   └── ... through lesson-90.html
├── graded-readers/     (12-chapter graded reader story)
│   ├── index.html      (reader table of contents)
│   └── chapter-01.html (... through chapter-12.html)
├── cheatsheets/        (88 lesson cheatsheets)
└── images/             (371 JPG visual aids)
```

## Usage

Open `index.html` in a web browser, or visit the deployed site. Navigate to individual lessons using the lesson list or prev/next links within each lesson.

## Notes

- No build system, dependencies, or tooling
- Lessons 28 and 45 do not exist in the original source material (88 lessons total)
- Images are referenced with relative paths from the lessons directory (`../images/`)
