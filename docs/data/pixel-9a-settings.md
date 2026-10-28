# Pixel 9a settings

The phone settings for every benchmark session ([capture protocol](capture-protocol.md) §3), and a short test series that checks them from the phone's own files. Every setting below was checked on 2026-10-28 against Google's help pages, recent reporting and the metadata of published full-size Pixel 9a photos; the numbers in brackets point to the [sources](#sources). What documentation can't settle, the [test series](#the-test-series) does.

**Menus moved in Pixel Camera 10.1.** "More settings" is now the three-dot button at the top right of the camera's settings sheet, and the old "Advanced" sub-menu is gone: its items are in one list, whose sections differ between phones [8]. So this sheet names each setting rather than giving a path. Open the camera, tap the settings button at the bottom left, then the three dots, and look for the name. If a setting is missing, note it for the test series.

## Once, before the first session

### In the camera: the settings sheet (bottom left)

| Setting | Set to | Why |
|---|---|---|
| Ratio | **Full image (4:3)** | The whole 4000 × 3000 frame; "Wide crop (16:9)" cuts the top and bottom [2] |
| Top Shot | **Off** (the circle with a line through it) | Otherwise the phone may save motion photos, with a short video added to each file [5, 9] |
| Night Sight | Tap Night Sight on the right, drag its slider **from Max to Off**, then set **More light** to **None** | In dim light Night Sight switches itself on and merges a long series of frames; on a still mount in the dark it can even switch to astrophotography [4] |
| Flash | **Off** | The light must not change between photos [2] |
| Timer | **Off** | The remote takes the photos [6] |

### In the camera: the three-dot list

| Setting | Set to | Why |
|---|---|---|
| Save location | **Off** | No location in any photo [2] |
| Ultra HDR | **Off** | With it on, every file carries a second, hidden image (an HDR "gain map") [10, 13] |
| RAW/JPEG control | **Off** | JPEG only; RAW adds a large DNG file next to each photo [2] |
| Volume key action | **Shutter** (the default) | The Bluetooth remote presses "volume up". Set to Zoom, every press would zoom [9] |
| Grid type | **3 × 3** | Helps keep the arm along its tape guide [9] |
| Framing hints | **On** while setting up the mount, **Off** for the blocks | Its level lines help square the phone, but it vibrates when level, which can nudge it [3, 9] |
| Quick access controls | **Off** (the default) | Otherwise a tap on the screen shows exposure and colour sliders that are easy to move by accident [9] |
| Rich colour in photos, Social media depth features | **Off**, if they are listed | Not every Pixel Camera version shows them; every photo should be plain sRGB with no depth data [12] |

### On the phone

| Setting | Set to | How |
|---|---|---|
| Google Photos backup | **Off** for the whole project | Google Photos → your profile picture (top right) → Photos settings → Backup → off. Check that Settings → System → Backup shows it off too [14] |
| Camera's location permission | **Don't allow** (optional, extra safety) | Settings → Apps → Camera → Permissions → Location |
| Bluetooth shutter | **Paired** | Settings → Connected devices → Pair new device → the remote's name [16]. If it has two buttons, use the one that takes a photo in the test series |
| Screen timeout | **30 minutes** on session days | Settings → Display & touch → Screen timeout. The viewfinder has to stay live through a 25-minute block |

## At the start of every block

1. **Do Not Disturb on**: swipe down from the top of the screen → Modes → Do Not Disturb [15]. A notification's vibration can shift the phone on its mount.
2. **Set which way is up before mounting.** Hold the phone the way the photos should come out (landscape), open the camera, then lower it onto the mount **without turning it**. Pointing straight down, the phone can't tell from gravity which way is up and may store a photo turned [17]. The ingest checks every photo for this, but it's better not to need it.
3. **Photo mode, 1×.** Not 0.5×, not 2×, not Portrait. Don't touch the screen during the block: a double tap zooms [2].
4. **Lock focus and exposure on the watch:** tap the watch on the screen, then tap **Lock** at the top right (or touch and hold until the circle turns yellow) [3, 7, 9]. Leave the brightness, shadow and white-balance sliders at their defaults.
5. **Slate:** one photo of the block's card, with the remote.

## The test series

Five minutes, once before the first session and again after any camera update. No wrist is needed: lay a watch on the backdrop.

1. Apply every setting above. Put the phone on the mount, straight down, about 30 cm above the watch, and lock focus and exposure on it.
2. Take **10 photos** with the remote, about 3 seconds apart, without touching anything.
3. Wait **2 minutes**. Check that the screen is still on and the viewfinder live, then take **2 more**.
4. Copy the 12 photos by USB into a new folder `raw/checks/<date>/` in the private store (not a session folder).
5. `uv run poe phone-check <that folder>` reads them and reports each check:

| Check | Passes when | Settles |
|---|---|---|
| camera, main lens, 1x zoom | Pixel 9a, 4.53 mm, no digital zoom | The lens and zoom never changed |
| full 4:3 frame, same way up, not upside down | 4000 × 3000, every photo the same size and the same way up | The ratio, and whether the phone keeps its orientation pointing down |
| plain photo mode | No `.NIGHT`, `.MP`, `.PORTRAIT` or `.RAW` in a file name, and no other files | Night Sight, Top Shot and RAW are off |
| location off | No latitude or longitude | Save location is off |
| Ultra HDR off | One image per file | Whether turning Ultra HDR off really removes the gain map |
| sRGB colour | An sRGB colour profile | Rich colour is off, or absent |
| not macro | Focus distance above 15 cm | The phone isn't too close |
| focus and exposure lock held | The same focus distance, exposure time and ISO in all 12 | Whether the lock survives a series of remote photos and a 2-minute wait |

**Result:** not run yet. It will be recorded here with the date and the Pixel Camera version (Settings → Apps → Camera → App details).

## What the phone writes

For reference, from the metadata of published full-size Pixel 9a photos [10]:

- **Image:** 4000 × 3000 JPEG (3000 × 4000 when held upright), sRGB, 3 to 5 MB. The phone writes the rotation into the pixels, so the orientation tag is always 1.
- **Lens:** focal length 4.53 mm (24 mm equivalent), lens model "Pixel 9a back camera 4.53mm f/1.7". The ultra-wide is 1.835 mm. At 2× the focal length stays 4.53 mm and only `DigitalZoomRatio` changes, to 2.0; the ingest checks it.
- **Focus:** `SubjectDistance` is the focus distance in metres, about 0.3 at the rig. Macro switches itself on only around 5 cm, on the main camera, and has no off switch on this phone [11]; at 30 cm it never triggers.
- **Time:** the file name's time is UTC; the EXIF time is local, with its offset.
- **Location:** files can carry a GPS block holding only a compass heading, even without a location. The ingest removes the whole block.
- **Always on, and harmless here:** every photo is a multi-frame HDR+ merge, which can't be switched off on this phone. There are no manual focus, shutter or ISO controls on the 9a [3].

## Sources

Read on 2026-10-28.

1. Pixel Phone Help, [Pixel phone hardware tech specs](https://support.google.com/pixelphone/answer/7158570): Pixel 9a cameras.
2. Pixel Camera Help, [Change your Camera app settings](https://support.google.com/pixelcamera/answer/2838995): ratio, save location, RAW, flash, grid, zoom gestures.
3. Pixel Camera Help, [Take high quality photos](https://support.google.com/pixelcamera/answer/14106982): focus lock, framing hints, Pro controls (Pro phones only).
4. Pixel Camera Help, [Take photos in low light or at night](https://support.google.com/pixelcamera/answer/9708795): automatic Night Sight and how to switch it off.
5. Pixel Camera Help, [Top Shot](https://support.google.com/pixelcamera/answer/9937175): settings for Pixel 9a and earlier.
6. Pixel Camera Help, [Timer](https://support.google.com/pixelcamera/answer/9937027).
7. Pixel Camera Help, [How to lock focus](https://support.google.com/pixelcamera/answer/18623896).
8. 9to5Google, [Pixel Camera 10.1 redesign](https://9to5google.com/2025/10/16/pixel-camera-10-1-material-3-expressive/), 2025-10-16: three-dot "More settings", the Advanced menu removed.
9. Android Authority, [Hidden Pixel Camera settings](https://www.androidauthority.com/hidden-google-pixel-camera-settings-3620687/), 2025-12-04: volume key action, grid, framing hints, quick access controls, touch-and-hold focus lock; Droid Life, [Pixel camera AI features](https://www.droid-life.com/2026/10/21/google-pixel-cameras-how-to-turn-off-the-ai-features/), 2026-10-21: switching Top Shot off.
10. GSMArena, [Pixel 9a review, camera samples](https://www.gsmarena.com/google_pixel_9a-review-2825p5.php), April 2025: full-size files, whose metadata was read for this sheet.
11. Android Authority, [Pixel 9a macro focus](https://www.androidauthority.com/google-pixel-9a-macro-mode-3535571/), 2025-03-19; 9to5Google, [Pixel 9a camera update](https://9to5google.com/2025/04/16/pixel-9a-camera-update/), 2025-04-16.
12. 9to5Google, [Pixel Camera 9.2](https://9to5google.com/2023/12/04/pixel-camera-9-2/), 2023-12-04: Ultra HDR and Rich colour toggles.
13. Android Developers, [Ultra HDR image format](https://developer.android.com/media/platform/hdr-image-format): the main image is plain SDR, the gain map an extra image.
14. Google Photos Help, [Back up photos and videos](https://support.google.com/photos/answer/6193313) and [Delete photos and videos](https://support.google.com/photos/answer/6128858): backup off; deleted items stay in the bin for 30 days.
15. Pixel Phone Help, [Modes and Do Not Disturb](https://support.google.com/pixelphone/answer/6111295).
16. Pixel Phone Help, [Connect through Bluetooth](https://support.google.com/pixelphone/answer/2819579).
17. Android Developers, [OrientationEventListener](https://developer.android.com/reference/android/view/OrientationEventListener): orientation can't be determined when the device lies close to flat.
