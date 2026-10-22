package app.td2drops;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Point;
import android.graphics.Rect;
import android.media.MediaMetadataRetriever;
import android.net.Uri;
import android.os.Build;

import com.google.android.gms.tasks.Tasks;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Reads an inventory video recorded on the console: follows the cursor ({@link VideoTracker}) and reads the
 * details panel with ML Kit's on-device text recognition (the model ships inside the app; no connection needed).
 */
public class VideoScanner {

    public interface Listener {
        void progress(int percent, String message);
    }

    private static final int W = 1920, H = 1080;
    private static final long STEP_MS = 333; // 3 frames per second

    private volatile boolean cancelled;

    public void cancel() {
        cancelled = true;
    }

    /** Returns the JSON for the web page: {ok, segments, duration, elapsed, frames, ocr} or {ok:false, error}. */
    public String scan(Context ctx, Uri uri, Listener listener) {
        long started = System.currentTimeMillis();
        MediaMetadataRetriever mmr = new MediaMetadataRetriever();
        TextRecognizer recognizer = null;
        try {
            mmr.setDataSource(ctx, uri);
            long durationMs = parse(mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION));
            int vw = (int) parse(mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH));
            int vh = (int) parse(mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT));
            long rot = parse(mmr.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION));
            if (rot == 90 || rot == 270) {
                int t = vw;
                vw = vh;
                vh = t;
            }
            if (durationMs <= 0 || vw <= 0 || vh <= 0) return error("This file doesn't look like a video.");
            double aspect = (double) vw / vh;
            if (Math.abs(aspect - 16.0 / 9.0) > 0.03)
                return error("The video must be a 16:9 capture from the console (this one is " + vw + "x" + vh + ").");

            recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
            VideoTracker tracker = new VideoTracker(0.7);
            int[] grid = new int[VideoTracker.GW * VideoTracker.GH];
            int[] panel = new int[VideoTracker.PW * VideoTracker.PH];
            int frames = 0, ocrCount = 0;

            for (long t = 0; t <= durationMs; t += STEP_MS) {
                if (cancelled) return error("cancelled");
                Bitmap frame = frameAt(mmr, t * 1000);
                if (frame == null) continue;
                try {
                    frame.getPixels(grid, 0, VideoTracker.GW, VideoTracker.GX, VideoTracker.GY, VideoTracker.GW, VideoTracker.GH);
                    frame.getPixels(panel, 0, VideoTracker.PW, VideoTracker.PX, VideoTracker.PY, VideoTracker.PW, VideoTracker.PH);
                    VideoTracker.Sample s = tracker.analyze(t / 1000.0, grid, panel);
                    if (tracker.add(s)) {
                        Bitmap crop = Bitmap.createBitmap(frame, VideoTracker.PX, VideoTracker.PY, VideoTracker.PW, VideoTracker.PH);
                        try {
                            tracker.addOcr(t / 1000.0, ocr(recognizer, crop));
                            ocrCount++;
                        } finally {
                            crop.recycle();
                        }
                    }
                } finally {
                    frame.recycle();
                }
                frames++;
                int pct = (int) Math.min(99, t * 100 / durationMs);
                listener.progress(pct, "Reading the video… " + (t / 1000) + " of " + (durationMs / 1000) + " s");
            }

            if (frames == 0) return error("Couldn't read the frames of this video.");
            JSONObject o = new JSONObject();
            o.put("ok", true);
            o.put("segments", new JSONArray(VideoTracker.toJson(tracker.finish())));
            o.put("duration", durationMs / 1000.0);
            o.put("elapsed", (System.currentTimeMillis() - started) / 1000.0);
            o.put("frames", frames);
            o.put("ocr", ocrCount);
            o.put("size", vw + "x" + vh);
            return o.toString();
        } catch (OutOfMemoryError e) {
            return error("Not enough memory to read this video.");
        } catch (Exception e) {
            String m = e.getMessage();
            return error("Couldn't read the video: " + (m == null || m.isEmpty() ? e.getClass().getSimpleName() : m));
        } finally {
            try {
                mmr.release();
            } catch (Exception ignored) {
            }
            if (recognizer != null) recognizer.close();
        }
    }

    /** One frame scaled to 1920x1080 (the size the tracker's coordinates are for). */
    private static Bitmap frameAt(MediaMetadataRetriever mmr, long us) {
        Bitmap b;
        if (Build.VERSION.SDK_INT >= 27) b = mmr.getScaledFrameAtTime(us, MediaMetadataRetriever.OPTION_CLOSEST, W, H);
        else b = mmr.getFrameAtTime(us, MediaMetadataRetriever.OPTION_CLOSEST);
        if (b == null) return null;
        if (b.getWidth() != W || b.getHeight() != H) {
            Bitmap s = Bitmap.createScaledBitmap(b, W, H, true);
            if (s != b) b.recycle();
            b = s;
        }
        return b;
    }

    /** Text lines of the panel with their boxes: [{t, x, y, w, h, a}] (a = angle in degrees). */
    private static String ocr(TextRecognizer recognizer, Bitmap panel) throws Exception {
        Text result = Tasks.await(recognizer.process(InputImage.fromBitmap(panel, 0)));
        JSONArray lines = new JSONArray();
        for (Text.TextBlock block : result.getTextBlocks()) {
            for (Text.Line line : block.getLines()) {
                Rect r = line.getBoundingBox();
                if (r == null) continue;
                JSONObject o = new JSONObject();
                o.put("t", line.getText());
                o.put("x", r.left);
                o.put("y", r.top);
                o.put("w", r.width());
                o.put("h", r.height());
                Point[] c = line.getCornerPoints();
                if (c != null && c.length >= 2) {
                    o.put("a", Math.round(Math.toDegrees(Math.atan2(c[1].y - c[0].y, c[1].x - c[0].x)) * 10) / 10.0);
                }
                lines.put(o);
            }
        }
        return lines.toString();
    }

    private static long parse(String s) {
        try {
            return s == null ? 0 : Long.parseLong(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static String error(String message) {
        try {
            JSONObject o = new JSONObject();
            o.put("ok", false);
            o.put("error", message);
            return o.toString();
        } catch (Exception e) {
            return "{\"ok\":false,\"error\":\"error\"}";
        }
    }
}
