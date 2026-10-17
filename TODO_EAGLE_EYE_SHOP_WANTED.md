# TODO — Eagle Eye Shop Most Wanted (future build prompt)

**Status:** Planned / **NOT IMPLEMENTED**. Do not enable or connect a camera until the user explicitly asks to build this feature.

## Context

Thermal Chaos is a local Flask/Pillow/ESC-POS receipt generator for an 80 mm Birch printer. The shop also has an **Eagle Eye PTZ camera**, intended to be mounted on top of the cabinets near the existing surveillance camera, above the Hungarian **"kamerával megfigyelt terület"** sign. The owner wants a hilarious **consensual, operator-approved thermal MOST WANTED souvenir**, with **Hungarian non-tech jokes**, never an unattended system that prints customers automatically.

The existing PHOTO > MOST WANTED mode has Hungarian shop/general/tech humor, randomly varied poster headings and fields, and the same preview/print pipeline. Reuse it; do not duplicate the poster renderer.

## Future ChatGPT implementation request

> Read the entire existing GitHub repository `Nemeth-Tamas/funwith80mm`, especially `app.py`, `wanted_posters.py`, `wanted_variations.py`, `static/index.html` and `tests/test_app.py`. Design and implement a **local-only, opt-in Eagle Eye camera capture workflow** for humorous Hungarian Most Wanted thermal souvenirs at Cellnet. Investigate the Eagle Eye model and the current EagleCast/PTZ project integration before selecting camera APIs. Get the owner to confirm connection details and the physical camera capabilities, such as RTSP/ONVIF or an existing PTZ interface, rather than inventing endpoints.
>
> Add a shop-operator UI with explicit **Arm / Következő áldozat**, live camera preview, a short delay, optional camera movement toward a consenting participant (person/face detection **only**; no identity matching or biometric recognition), snapshot, and **a frozen wanted-poster preview** generated through the existing app. Only accept **Nyomtatás** after a separate deliberate click; provide **Új szöveg** (keep same snapshot; regenerate non-tech Hungarian jokes), **Újrafotózás**, and **Mégse**. A print action must never be triggered automatically by motion, a face, timeouts, or a camera event.
>
> Default to Hungarian **shop/non-tech** comic content. A manually selectable joke level is nice to have but not required. The customer should be aware of and agree to the novelty photo before capture; the surveillance sign alone is not sufficient consent to make a souvenir. Do **not** retain/store faces, identify visitors, log biometric descriptors, silently record everyone, or expose the camera feed outside 127.0.0.1. Buffer snapshots in memory, clear on cancellation and shortly after printing, and allow immediate disarm. Never aim an active PTZ at arbitrary uninvolved customers; require operator targeting/consent or a tightly restricted participant-only zone.
>
> Retain existing 576-pixel raster width, Pillow grayscale/dithering, image-cache preview/print correspondence, bottom margin (12/20/30 mm), Windows-installed USB/network queue selection, and optional cutter. Treat camera disconnection, tracking failure, poor lighting, multiple people, unavailable PTZ, and printer errors gracefully. If PTZ controls are unavailable, allow manual aim and single-frame capture. Keep tests mocked/offline, with no physical camera or printer needed, and ensure no auto-print call without confirmation. Update README and CI. The camera integration must be opt-in and disabled by default.

## Acceptance checklist

- [ ] Confirm the exact Eagle Eye/EagleCast camera model, stream and PTZ API.
- [ ] Deliberate operator arm + participant awareness/consent + one-shot capture/disarm.
- [ ] No face identification, automatic face archives, or always-on captures.
- [ ] Operator-only preview: **Nyomtatás / Új szöveg / Újrafotózás / Mégse**.
- [ ] Hungarian non-tech Most Wanted default. Existing `wanted_profile` pools reusable.
- [ ] Local memory-only snapshots, cleanup on cancel and timeout, safe error handling.
- [ ] Preserve USB/network Birch output, 576 px, cutter, preview, padding.
- [ ] Mocked offline tests proving camera events cannot trigger print.
- [ ] README/setup, UI instructions and GitHub Actions green.

## Not part of this TODO

Nothing here authorizes implementing or activating surveillance today. This is a saved future implementation brief; the current project only generates posters from operator-uploaded photos.
