# Participant information: Lug to Lug wrist benchmark

What every participant is told before their first photo, and agrees to in person ([ADR-0012](../decisions/0012-agreement-in-person.md)). Nothing is signed.

---

### What this is

Lug to Lug is a personal software project by Vinayak Mokashi: a watch try-on that shows any watch on a photo of your wrist at its true size. To prove that its sizing is accurate, it needs photos of real wrists wearing watches of known size.

### What taking part involves

- **Photos of your wrist and forearm** (your hand may be in them) wearing a series of watches, taken from above with a phone on a stand. Your face is not photographed. A session takes about 15 to 30 minutes.
- **Measurements of your wrist:** the circumference with a soft tape, and the width of your wrist and hand with calipers.
- **Your skin tone as a group** on the Monk Skin Tone scale, where you choose the closest swatch. It is used only to check that the app works equally well for everyone, and results are reported for groups, never for one person.

You need to be 18 or older to take part. You can cover tattoos or other marks if you prefer, and you can stop at any point.

### How your data is used

- Your photos and measurements are used to measure how accurate the app is (the benchmark) and to train or tune its models. If you would rather stay out of training, say so, and they are used for the benchmark only.
- The numbers and outlines measured from your photos (no images) are published as part of the benchmark, under your participant ID only.
- A photo of your wrist, cropped to your wrist and the watch, is published in the public benchmark or on the project's pages only if you say yes. Saying nothing means no.

### How your data is kept

- Everywhere in the project you are identified only by your participant ID. Your name stays in the project's private notes.
- Your photos are stored privately, outside the public code repository: on the project owner's computer, with a backup in the owner's private Google Drive that is shared with no one. They are processed only for this project, on the cloud services it uses (for example Google Cloud, Modal, Kaggle and AI model APIs), and are never sold or shared for any other purpose.
- Location data is removed from every photo.
- Your data is kept until the project ends or until you withdraw, whichever comes first, and is then deleted.

### Withdrawing

You can withdraw at any time without giving a reason, by telling Vinayak. Within 14 days your photos and measurements are deleted from the computer and from the backup, and they are left out of every later release of the benchmark. Anything published with your permission is taken down from the project's own pages, but copies other people have already made cannot be recalled. Your photos will not be used for any new training; a model already trained with them is used only until its next update.
