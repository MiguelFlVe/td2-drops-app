package app.td2drops;

import java.util.ArrayList;
import java.util.List;

/**
 * Follows the cursor through an inventory video and tells which items were new.
 *
 * Pure Java (no Android classes) so it can be tested on a computer with frames from a real clip.
 * All coordinates are for a 1920x1080 frame; the caller scales the video to that size.
 *
 * How it works:
 *  - The selected item is the large bright orange tile in the item grid.
 *  - A new (unseen) item has a small orange badge with a white "!" in its top-right corner. The game removes it
 *    as soon as the item is selected, so an item was new if its tile had the badge just before the cursor got there.
 *  - The cursor stays on an item for a while (the player reads the details panel): that's a "segment".
 *  - If the list scrolled between those two moments, the tile is looked up where it was before the scroll; if it
 *    wasn't on screen, the result is "unsure".
 *  - While the cursor rests on an item, the details panel is read (OCR) whenever its content changes.
 */
public class VideoTracker {

    // Item grid and details panel (1080p)
    public static final int GX = 830, GY = 160, GW = 600, GH = 680;
    public static final int PX = 1450, PY = 140, PW = 430, PH = 730;

    // Tile columns (centre x) and sizes
    private static final int[] COL_CX = {975, 1268};
    private static final int COL_TOL = 70;

    public static final int NEW = 1, OLD = 0, UNSURE = 2;

    /** One analysed frame. */
    public static class Sample {
        public double t;
        public int[] sel;            // x, y, w, h of the selected tile (1080p), or null
        public List<int[]> badges;   // centres of new-item badges outside the selected tile
        float[][] profile;           // [col][row] mean luminance, NaN where a selected tile covers it
        float[] tileSig;             // look of the selected tile (to notice a change while the cursor stays put)
        float[] panelSig;            // look of the details panel (to decide when to read it again)
    }

    /** One item the cursor rested on. */
    public static class Segment {
        public double t0, t1;
        public int[] sel;
        public int status = OLD;
        public String why = "";
        public final List<String> ocr = new ArrayList<>(); // JSON array per OCR'd frame
        public final List<Double> ocrTimes = new ArrayList<>();
        float[] lastOcrSig;
        double lastOcrT;
        int firstSample;
    }

    private final List<Sample> samples = new ArrayList<>();
    private final List<Segment> segments = new ArrayList<>();
    private Segment open;
    private final double minDwell;

    public VideoTracker(double minDwellSeconds) {
        this.minDwell = minDwellSeconds;
    }

    // ------------------------------------------------------------------ pixel tests

    private static boolean orange(int p) {
        int r = (p >> 16) & 255, g = (p >> 8) & 255, b = p & 255;
        return r > 200 && g > 50 && g < 150 && b < 80;
    }

    private static boolean white(int p) {
        int r = (p >> 16) & 255, g = (p >> 8) & 255, b = p & 255;
        return r > 230 && g > 190 && b > 150;
    }

    private static float lum(int p) {
        return 0.299f * ((p >> 16) & 255) + 0.587f * ((p >> 8) & 255) + 0.114f * (p & 255);
    }

    /** Connected components of orange pixels in the grid. Returns {x, y, w, h, area, whitePixels} in grid coords. */
    private final boolean[] seen = new boolean[GW * GH];
    private final int[] stack = new int[GW * GH];

    private List<int[]> orangeBlobs(int[] grid) {
        List<int[]> out = new ArrayList<>();
        java.util.Arrays.fill(seen, false);
        for (int start = 0; start < GW * GH; start++) {
            if (seen[start] || !orange(grid[start])) continue;
            int sp = 0, minx = GW, miny = GH, maxx = -1, maxy = -1, area = 0;
            stack[sp++] = start;
            seen[start] = true;
            while (sp > 0) {
                int i = stack[--sp];
                int x = i % GW, y = i / GW;
                area++;
                if (x < minx) minx = x;
                if (x > maxx) maxx = x;
                if (y < miny) miny = y;
                if (y > maxy) maxy = y;
                for (int k = 0; k < 8; k++) {
                    int nx = x + (k == 0 || k == 3 || k == 5 ? -1 : k == 2 || k == 4 || k == 7 ? 1 : 0);
                    int ny = y + (k < 3 ? -1 : k > 4 ? 1 : 0);
                    if (nx < 0 || ny < 0 || nx >= GW || ny >= GH) continue;
                    int j = ny * GW + nx;
                    if (!seen[j] && orange(grid[j])) {
                        seen[j] = true;
                        stack[sp++] = j;
                    }
                }
            }
            int w = maxx - minx + 1, h = maxy - miny + 1;
            int whites = 0;
            if (w <= 24 && h <= 36) {
                for (int y = miny; y <= maxy; y++)
                    for (int x = minx; x <= maxx; x++) if (white(grid[y * GW + x])) whites++;
            }
            out.add(new int[]{minx, miny, w, h, area, whites});
        }
        return out;
    }

    private static int column(int[] sel) {
        int cx = sel[0] + sel[2] / 2;
        for (int c = 0; c < COL_CX.length; c++) if (Math.abs(cx - COL_CX[c]) <= COL_TOL) return c;
        return -1;
    }

    private static boolean inside(int x, int y, int[] box, int pad) {
        return box != null && x >= box[0] - pad && x <= box[0] + box[2] + pad && y >= box[1] - pad && y <= box[1] + box[3] + pad;
    }

    // ------------------------------------------------------------------ analysis

    /**
     * Analyses one frame.
     * @param grid  pixels of the grid area (GW x GH, ARGB), from (GX, GY) of a 1920x1080 frame
     * @param panel pixels of the details panel (PW x PH, ARGB), from (PX, PY); may be null
     */
    public Sample analyze(double t, int[] grid, int[] panel) {
        Sample s = new Sample();
        s.t = t;
        List<int[]> blobs = orangeBlobs(grid);
        int[] best = null;
        for (int[] b : blobs) {
            if (b[4] > 8000 && b[2] > 150 && b[2] < 330 && b[3] > 60 && b[3] < 130 && (best == null || b[4] > best[4])) best = b;
        }
        if (best != null) {
            int[] sel = {best[0] + GX, best[1] + GY, best[2], best[3]};
            if (column(sel) >= 0) s.sel = sel;
        }
        s.badges = new ArrayList<>();
        for (int[] b : blobs) {
            if (b[2] >= 7 && b[2] <= 22 && b[3] >= 16 && b[3] <= 34 && b[4] >= 60 && b[5] >= 6) {
                int cx = b[0] + b[2] / 2 + GX, cy = b[1] + b[3] / 2 + GY;
                if (!inside(cx, cy, s.sel, 2)) s.badges.add(new int[]{cx, cy});
            }
        }
        // Row profiles of both columns (for scroll detection), skipping the selected tile
        s.profile = new float[2][GH];
        for (int c = 0; c < 2; c++) {
            int x0 = COL_CX[c] - 110 - GX, x1 = COL_CX[c] + 110 - GX;
            for (int y = 0; y < GH; y++) {
                if (s.sel != null && column(s.sel) == c && y + GY >= s.sel[1] - 6 && y + GY <= s.sel[1] + s.sel[3] + 6) {
                    s.profile[c][y] = Float.NaN;
                    continue;
                }
                float sum = 0;
                int n = 0;
                for (int x = x0; x < x1; x += 2) {
                    sum += lum(grid[y * GW + x]);
                    n++;
                }
                s.profile[c][y] = sum / n;
            }
        }
        if (s.sel != null) s.tileSig = tileSignature(grid, s.sel);
        if (panel != null) s.panelSig = signature(panel, PW, PH, 0, 0, PW, PH, 16, 28);
        return s;
    }

    /** Coarse grey thumbnail (cols x rows cells) of a box. */
    private static float[] signature(int[] px, int stride, int height, int x0, int y0, int w, int h, int cols, int rows) {
        float[] sig = new float[cols * rows];
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                int xa = x0 + c * w / cols, xb = x0 + (c + 1) * w / cols;
                int ya = y0 + r * h / rows, yb = y0 + (r + 1) * h / rows;
                float sum = 0;
                int n = 0;
                for (int y = Math.max(0, ya); y < Math.min(height, yb); y += 2)
                    for (int x = Math.max(0, xa); x < Math.min(stride, xb); x += 2) {
                        sum += lum(px[y * stride + x]);
                        n++;
                    }
                sig[r * cols + c] = n == 0 ? 0 : sum / n;
            }
        }
        return sig;
    }

    /** Thumbnail of a fixed-size box around the tile centre (robust to the selection zoom animation). */
    private static float[] tileSignature(int[] grid, int[] sel) {
        int cx = sel[0] + sel[2] / 2 - GX, cy = sel[1] + sel[3] / 2 - GY;
        return signature(grid, GW, GH, cx - 100, cy - 36, 200, 72, 20, 6);
    }

    private static float diff(float[] a, float[] b) {
        if (a == null || b == null || a.length != b.length) return 999;
        float d = 0;
        for (int i = 0; i < a.length; i++) d += Math.abs(a[i] - b[i]);
        return d / a.length;
    }

    /** Vertical scroll between two frames, in pixels (content moved down by the result), or Integer.MIN_VALUE. */
    static int scrollBetween(Sample a, Sample b) {
        double zeroErr = scrollErr(a, b, 0);
        if (Double.isNaN(zeroErr)) return Integer.MIN_VALUE;
        if (zeroErr < 2.5) return 0; // nothing moved
        int best = 0;
        double bestErr = zeroErr;
        for (int d = -150; d <= 150; d += 3) {
            double e = scrollErr(a, b, d);
            if (!Double.isNaN(e) && e < bestErr) { bestErr = e; best = d; }
        }
        for (int d = best - 2; d <= best + 2; d++) {
            double e = scrollErr(a, b, d);
            if (!Double.isNaN(e) && e < bestErr) { bestErr = e; best = d; }
        }
        // Prefer "no scroll" unless another shift is clearly better
        if (best != 0 && zeroErr < bestErr * 1.5 + 2) return 0;
        return best;
    }

    private static double scrollErr(Sample a, Sample b, int d) {
        double err = 0;
        int n = 0;
        for (int c = 0; c < 2; c++) {
            for (int y = 0; y < GH; y += 2) {
                int y2 = y + d;
                if (y2 < 0 || y2 >= GH) continue;
                float p = a.profile[c][y], q = b.profile[c][y2];
                if (Float.isNaN(p) || Float.isNaN(q)) continue;
                err += Math.abs(p - q);
                n++;
            }
        }
        return n < 150 ? Double.NaN : err / n;
    }

    /** How different two frames' details panels look (0 = identical). */
    public static float panelDiff(Sample a, Sample b) {
        return diff(a.panelSig, b.panelSig);
    }

    private static boolean samePlace(int[] a, int[] b) {
        return a != null && b != null && Math.abs((a[0] + a[2] / 2) - (b[0] + b[2] / 2)) < 60
                && Math.abs((a[1] + a[3] / 2) - (b[1] + b[3] / 2)) < 45;
    }

    // ------------------------------------------------------------------ segments

    /**
     * Adds an analysed frame. Returns true if the caller should read (OCR) the details panel of this frame
     * and pass the result to {@link #addOcr}.
     */
    public boolean add(Sample s) {
        Sample prev = samples.isEmpty() ? null : samples.get(samples.size() - 1);
        samples.add(s);
        if (s.sel == null) {
            closeOpen();
            return false;
        }
        boolean same = false;
        if (open != null && prev != null && prev.sel != null && samePlace(prev.sel, s.sel)) {
            // Same spot: still the same item unless the list scrolled under the cursor
            int d = scrollBetween(prev, s);
            same = d == 0 || d == Integer.MIN_VALUE;
        }
        if (!same) {
            closeOpen();
            open = new Segment();
            open.t0 = s.t;
            open.t1 = s.t;
            open.sel = s.sel;
            open.firstSample = samples.size() - 1;
            return false; // the panel may still be animating: read it from the next frame on
        }
        open.t1 = s.t;
        // Read the panel the first time, then again each time it has scrolled to show something new
        if (open.lastOcrSig == null) return true;
        return diff(open.lastOcrSig, s.panelSig) > 8 && s.t - open.lastOcrT >= 0.5;
    }

    /** OCR result of the last added frame: a JSON array of {t,x,y,w,h} objects (panel coordinates). */
    public void addOcr(double t, String linesJson) {
        if (open == null) return;
        open.ocr.add(linesJson);
        open.ocrTimes.add(t);
        open.lastOcrSig = samples.get(samples.size() - 1).panelSig;
        open.lastOcrT = t;
    }

    private void closeOpen() {
        if (open == null) return;
        if (open.t1 - open.t0 >= minDwell) {
            judge(open);
            segments.add(open);
        }
        open = null;
    }

    /** Decides whether the item of a segment was new, looking at the frames just before it was selected. */
    private void judge(Segment seg) {
        Sample cur = samples.get(seg.firstSample);
        int checked = 0;
        for (int j = seg.firstSample - 1; j >= 0 && checked < 3; j--) {
            Sample p = samples.get(j);
            if (p.sel == null) break; // menu or another screen in between: can't tell
            checked++;
            int d = scrollBetween(p, cur);
            if (d == Integer.MIN_VALUE) {
                seg.status = UNSURE;
                seg.why = "scroll";
                continue;
            }
            // Where this tile was in the earlier frame
            int[] box = {seg.sel[0], seg.sel[1] - d, seg.sel[2], seg.sel[3]};
            if (box[1] < GY || box[1] + box[3] > GY + GH) {
                seg.status = UNSURE;
                seg.why = "offscreen";
                return;
            }
            if (samePlace(p.sel, box)) {
                // The earlier frame had the cursor on that same spot: it's the previous item (no scroll) -> look further back
                if (d == 0) continue;
                seg.status = UNSURE;
                seg.why = "covered";
                return;
            }
            for (int[] b : p.badges) {
                if (inside(b[0], b[1], box, 10)) {
                    seg.status = NEW;
                    seg.why = "";
                    return;
                }
            }
            seg.status = OLD;
            seg.why = "";
            return;
        }
        if (checked == 0) {
            seg.status = UNSURE;
            seg.why = "start";
        }
    }

    /** Closes the last segment and returns all of them. */
    public List<Segment> finish() {
        closeOpen();
        return segments;
    }

    /** Segments as JSON for the web page. */
    public static String toJson(List<Segment> segs) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < segs.size(); i++) {
            Segment s = segs.get(i);
            if (i > 0) sb.append(',');
            sb.append("{\"t0\":").append(round(s.t0)).append(",\"t1\":").append(round(s.t1))
                    .append(",\"status\":\"").append(s.status == NEW ? "new" : s.status == OLD ? "old" : "unsure").append('"')
                    .append(",\"why\":\"").append(s.why).append('"')
                    .append(",\"tile\":[").append(s.sel[0]).append(',').append(s.sel[1]).append(',').append(s.sel[2]).append(',').append(s.sel[3]).append(']')
                    .append(",\"frames\":[");
            for (int k = 0; k < s.ocr.size(); k++) {
                if (k > 0) sb.append(',');
                sb.append("{\"t\":").append(round(s.ocrTimes.get(k))).append(",\"lines\":").append(s.ocr.get(k)).append('}');
            }
            sb.append("]}");
        }
        return sb.append(']').toString();
    }

    private static String round(double v) {
        return String.valueOf(Math.round(v * 100) / 100.0);
    }
}
