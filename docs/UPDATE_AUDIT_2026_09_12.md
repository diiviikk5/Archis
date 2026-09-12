# Updated desktop audit

Reviewed the Fluent desktop shell and NanoSpot integration at baseline 969e970.
This is a focused implementation audit, not certification of all README claims.

## Completed in this pass

- Continuous accumulated trajectory phase: live speed changes no longer rewrite
  elapsed motion for circular and figure-eight paths.
- Spiral expansion/contraction is continuous rather than periodically wrapping.
- Sinusoidal motion now follows a bounded oscillating path instead of wrapping
  horizontal coordinates outside the world. This changes that preset's path.
- Straight-line bounce direction survives numerical velocity calculation; live
  speed edits apply on the next frame.
- Fixed sensor-period simulation steps prevent UI stalls from advancing a large
  jump. Under overload playback slows; this is not a hard real-time guarantee.
- Explicit quarter-, half-, and real-time playback controls, including video.
  Playback pacing does not alter the sensor period supplied to tracking logic.
- Startup state reflects the tracker rather than claiming immediate lock.
- Viewport scaling, reticle center and click bounds use actual frame dimensions;
  smooth image scaling affects presentation only, not detector input.

## Remaining delivery gates

1. Processing still runs on the UI thread. Move ownership of the tracker and
   source into a worker with bounded frame delivery and explicit shutdown.
2. Imported video has playback but no reference-centroid CSV scoring or annotated
   export workflow. Do not equate simulated pointing error with reference error.
3. Validate atmosphere realism and reproducibility; these motion repairs do not
   establish physical turbulence or calibrated optical exposure models.
4. Validate AI accuracy, confidence and decoy rejection on independent data;
   passing the current unit tests is not evidence of generalization.
5. Reconcile the older overhaul checklist against implemented interfaces, then
   verify packaging, bundled assets and dependencies on a clean Windows machine.
6. Perform visible desktop QA at minimum and full window sizes and display scaling.
   Offscreen widget tests are not a substitute for that visual acceptance pass.

The complete overhaul remains open; no blanket compliance claim is made here.
