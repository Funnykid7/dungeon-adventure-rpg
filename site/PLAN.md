# 🏰 Liquid Glass Site Plan

## Design Language
- **Theme**: Void-Depth (Pure black background with glowing glass overlays).
- **Core Aesthetic**: Liquid Glass. High-blur (`24px`) containers with very rounded edges (`30px` to `50px`).
- **Typography**: Cinzel (Fantasy/Gothic) for headers, Inter (Modern/Clean) for bodies.
- **Accents**: Neon Cyan (`#00f3ff`) for active elements, Neon Magenta (`#ff0064`) for status.

## File Structure
- `index.html`: Hybrid single-page structure.
- `css/styles.css`: Glassmorphism utilities, animated radial glows, and responsive grid layouts.
- `js/app.js`: GitHub API integration for live "Bounty Board" (issues) and ambient parallax scroll effects.

## Good Ideas Implemented
1. **Ambient Parallax Glow**: Background "magical auras" that subtly move as the user scrolls, creating a sense of depth in the "dungeon".
2. **Live Bounty Board**: Instead of a static issues list, we fetch them dynamically so potential contributors see fresh tasks instantly.
3. **Responsive Glass Grid**: A flexible feature grid that maintains the glass aesthetic across mobile and desktop.
4. **Animated Status Badge**: A pulsing magenta indicator that visually signals the project's active development phase.

## Usage
Simply host the contents of this folder on **GitHub Pages** (Settings > Pages > Deploy from branch).
