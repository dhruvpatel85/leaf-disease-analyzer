#!/usr/bin/env python3
"""
Potato Leaf Disease Analyzer — v4
====================================
Multi-feature HSV analysis:
  - Separate brown-spot detector  → Early Blight
  - Dark-green-patch detector     → Late Blight
  - Texture/variance analysis
  - Smart background removal
  - Auto-installs Pillow if missing
Outputs ONE JSON line to stdout. All other output suppressed.
"""

import os, sys, json, math, warnings, colorsys, subprocess

# ── Silence everything ─────────────────────────────────────────────────────
os.environ.update({
    'TF_CPP_MIN_LOG_LEVEL':  '3',
    'TF_ENABLE_ONEDNN_OPTS': '0',
    'CUDA_VISIBLE_DEVICES':  '-1',
    'MPLBACKEND':            'Agg',
    'PYTHONWARNINGS':        'ignore',
    'MPLCONFIGDIR':          '/tmp/matplotlib_cache',
})
warnings.filterwarnings("ignore")
_orig_stderr = sys.stderr
try:
    sys.stderr = open(os.devnull, 'w')
except Exception:
    pass
os.makedirs('/tmp/matplotlib_cache', mode=0o755, exist_ok=True)


# ── Auto-install Pillow ────────────────────────────────────────────────────
def ensure_pillow():
    try:
        from PIL import Image  # noqa
        return True
    except ImportError:
        pass
    try:
        r = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'pillow',
             '--quiet', '--disable-pip-version-check'],
            capture_output=True, timeout=120
        )
        if r.returncode == 0:
            from PIL import Image  # noqa
            return True
    except Exception:
        pass
    return False


# ── Disease knowledge base ─────────────────────────────────────────────────
DISEASE_INFO = {
    "Early Blight": {
        "description": (
            "Early Blight is caused by the fungus Alternaria solani. "
            "It appears as dark brown to black spots with concentric rings "
            "(target-like pattern) typically starting on older, lower leaves."
        ),
        "solution": (
            "1. Remove and destroy affected leaves immediately.\n"
            "2. Apply fungicide (Chlorothalonil or Mancozeb) every 7-10 days.\n"
            "3. Ensure proper spacing between plants for air circulation.\n"
            "4. Water at the base of plants — avoid wetting leaves.\n"
            "5. Use crop rotation: avoid planting potatoes in the same spot for 2-3 years.\n"
            "6. Apply mulch to prevent soil-borne spores from splashing onto leaves."
        ),
        "severity": "Moderate",
    },
    "Late Blight": {
        "description": (
            "Late Blight is caused by Phytophthora infestans. It produces large, "
            "dark, water-soaked lesions that spread rapidly across the leaf. "
            "White mold may appear on the underside in humid conditions."
        ),
        "solution": (
            "1. Remove and destroy ALL infected plants immediately — do NOT compost them.\n"
            "2. Apply fungicide (Metalaxyl or Copper-based) right away.\n"
            "3. Ensure excellent drainage and avoid overhead irrigation.\n"
            "4. Plant resistant potato varieties (e.g., Sarpo Mira, Defender).\n"
            "5. Monitor weather — cool, wet conditions favour this disease.\n"
            "6. Act FAST — Late Blight can destroy an entire crop within days."
        ),
        "severity": "Severe",
    },
    "Healthy": {
        "description": "The leaf appears healthy with no visible signs of disease.",
        "solution": (
            "Your plant looks healthy! To keep it that way:\n"
            "1. Water regularly but avoid overwatering.\n"
            "2. Ensure adequate sunlight (6-8 hours daily).\n"
            "3. Apply balanced fertilizer every 2-3 weeks.\n"
            "4. Monitor regularly for early signs of disease.\n"
            "5. Practice crop rotation each season."
        ),
        "severity": "None",
    },
}

CLASS_NAMES = ["Early Blight", "Late Blight", "Healthy"]
MODEL_PATH  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaf_disease_model.keras")


# ── ML inference (used only if .keras model file exists) ──────────────────
def analyze_with_ml(image_path):
    try:
        import numpy as np
        from tensorflow.keras.models import load_model
        from tensorflow.keras.preprocessing import image as ki
    except ImportError as e:
        return None, f"TensorFlow not installed: {e}"
    if not os.path.isfile(MODEL_PATH):
        return None, "Model not found"
    try:
        model = load_model(MODEL_PATH, compile=False)
        img   = ki.load_img(image_path, target_size=(224, 224))
        arr   = ki.img_to_array(img) / 255.0
        import numpy as np
        preds = model.predict(np.expand_dims(arr, 0), verbose=0)
        idx   = int(np.argmax(preds[0]))
        conf  = float(np.max(preds[0])) * 100.0
        if idx >= len(CLASS_NAMES):
            return None, f"Bad class index: {idx}"
        return CLASS_NAMES[idx], round(conf, 1)
    except Exception as e:
        return None, f"ML error: {e}"


# ── Smart HSV color analysis ───────────────────────────────────────────────
def analyze_leaf_color(image_path):
    try:
        from PIL import Image
    except ImportError:
        return None, "Pillow unavailable"

    try:
        img  = Image.open(image_path).convert("RGB")
        w, h = img.size

        # Remove background (crop inner 70%)
        crop = img.crop((w * 0.15, h * 0.15, w * 0.85, h * 0.85))
        if crop.size[0] < 30 or crop.size[1] < 30:
            crop = img

        analysis = crop.resize((200, 200), Image.LANCZOS)
        pixels   = list(analysis.getdata())
        total    = len(pixels)

        # ── HSV pixel classification ───────────────────────────────────────
        # healthy_green     : bright pure green (h=80–150°, s>0.25, v>0.35)
        # dark_green_lesion : dark water-soaked green (h=80–150°, s>0.20, v≤0.35) → Late Blight
        # yellow_green      : stressed tissue (h=45–80°, s>0.15)
        # yellow            : chlorosis (h=30–55°, s>0.20, v>0.30)
        # necrotic_brown    : dead/necrotic tissue (h<35° or h>320°, s>0.15) → Early Blight
        # dark_grey         : very dark dead cells (v<0.20, s<0.20)
        # background        : bright & desaturated (v>0.85, s<0.15) — excluded

        hg = dgl = yg = y = nb = dg = bg = 0

        for r, g, b in pixels:
            hv, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            hd = hv * 360

            if v > 0.85 and s < 0.15:                           bg  += 1
            elif 80 <= hd <= 150 and s > 0.25 and v > 0.35:    hg  += 1
            elif 80 <= hd <= 150 and s > 0.20 and v <= 0.35:   dgl += 1  # ← Late Blight
            elif 45 <= hd < 80  and s > 0.15:                   yg  += 1
            elif 30 <= hd < 55  and s > 0.20 and v > 0.30:     y   += 1
            elif (hd < 35 or hd > 320) and s > 0.15 and v > 0.15: nb += 1  # ← Early Blight
            elif v < 0.20 and s < 0.20:                          dg  += 1

        # Use leaf-only pixels (exclude background)
        leaf_total = max(1, total - bg)

        hg_p  = hg  / leaf_total * 100
        dgl_p = dgl / leaf_total * 100   # dark water-soaked green → Late Blight
        yg_p  = yg  / leaf_total * 100
        y_p   = y   / leaf_total * 100
        nb_p  = nb  / leaf_total * 100   # brown necrosis → Early Blight
        dg_p  = dg  / leaf_total * 100
        diseased_p = dgl_p + yg_p + y_p + nb_p + dg_p

        # ── Spot/patch detection (100×100 sample) ─────────────────────────
        sample  = crop.resize((100, 100), Image.LANCZOS)
        spx     = list(sample.getdata())
        S       = 100
        brown_spots = 0   # discrete brown spots → Early Blight
        dg_patches  = 0   # dark-green patches → Late Blight

        for row in range(2, S - 2):
            for col in range(2, S - 2):
                idx_c      = row * S + col
                r_c, g_c, b_c = spx[idx_c]
                hvc, sc, vc = colorsys.rgb_to_hsv(r_c/255, g_c/255, b_c/255)
                hdc = hvc * 360

                is_brown = (hdc < 35 or hdc > 320) and sc > 0.20 and vc > 0.15
                is_dg    = 80 <= hdc <= 150 and sc > 0.20 and vc < 0.30

                if not (is_brown or is_dg):
                    continue

                # Count bright-green neighbours — confirms spot on green leaf
                bright_green_n = 0
                for dr in (-2, -1, 1, 2):
                    for dc in (-2, -1, 1, 2):
                        ni = (row + dr) * S + (col + dc)
                        if 0 <= ni < S * S:
                            rn, gn, bn = spx[ni]
                            hvn, sn, vn = colorsys.rgb_to_hsv(rn/255, gn/255, bn/255)
                            if 80/360 <= hvn <= 150/360 and sn > 0.15 and vn > 0.35:
                                bright_green_n += 1

                if bright_green_n >= 2:
                    if is_brown: brown_spots += 1
                    if is_dg:    dg_patches  += 1

        bs_den = brown_spots / (S * S) * 1000   # brown spot density
        dg_den = dg_patches  / (S * S) * 1000   # dark-green patch density

        # ── Scoring ───────────────────────────────────────────────────────
        # Late Blight: dark water-soaked green + dark grey + yellowing border + dg patches
        lb_score = (dgl_p * 3.5 + dg_p * 2.0 + dg_den * 0.5 +
                    yg_p  * 0.4 + max(0, 60 - hg_p) * 0.2)

        # Early Blight: brown necrosis + yellow halo + brown spot density
        eb_score = (nb_p * 3.5 + y_p * 1.5 + bs_den * 1.5 + yg_p * 0.3)

        # Healthy: high bright green, low disease, few spots
        h_score  = max(0, hg_p * 1.5 - diseased_p * 0.7 - (bs_den + dg_den) * 1.5)

        # ── Decision + confidence ─────────────────────────────────────────
        if (h_score >= lb_score and h_score >= eb_score and
                diseased_p < 25 and (bs_den + dg_den) < 3.0):
            label = "Healthy"
            conf  = min(95.0, max(55.0, 50.0 + hg_p * 0.5 - diseased_p * 0.5))

        elif lb_score >= eb_score:
            label = "Late Blight"
            evidence = dgl_p * 1.8 + dg_p * 0.8 + yg_p * 0.3 + dg_den * 0.2
            conf  = min(92.0, max(55.0, 40.0 + evidence))

        else:
            label = "Early Blight"
            evidence = nb_p * 2.5 + bs_den * 1.5 + y_p * 0.8
            conf  = min(92.0, max(55.0, 35.0 + evidence))

        # ── Debug log (silent) ────────────────────────────────────────────
        try:
            with open("/tmp/leaf_analysis_debug.log", "a") as f:
                f.write(
                    f"\n[{os.path.basename(image_path)}]\n"
                    f"  hg={hg_p:.1f}% dgl={dgl_p:.1f}% nb={nb_p:.1f}% "
                    f"yg={yg_p:.1f}% y={y_p:.1f}% dg={dg_p:.1f}%\n"
                    f"  diseased={diseased_p:.1f}% bs_den={bs_den:.1f} dg_den={dg_den:.1f}\n"
                    f"  scores H={h_score:.1f} EB={eb_score:.1f} LB={lb_score:.1f}\n"
                    f"  → {label} ({conf:.1f}%)\n"
                )
        except Exception:
            pass

        return label, round(conf, 1)

    except Exception as e:
        return None, f"Color analysis error: {e}"


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: analyze_leaf.py <image_path>"}))
        sys.exit(1)

    image_path = sys.argv[1]
    if not os.path.isfile(image_path):
        print(json.dumps({"error": f"Image not found: {image_path}"}))
        sys.exit(1)

    # 1. Try ML model
    label, info = analyze_with_ml(image_path)

    # 2. Fall back to smart color analysis
    if label is None:
        if not ensure_pillow():
            print(json.dumps({
                "error": (
                    f"Pillow is not installed.\n"
                    f"Fix: Open Terminal and run:\n  {sys.executable} -m pip install pillow"
                )
            }))
            sys.exit(1)
        label, info = analyze_leaf_color(image_path)

    if label is None:
        print(json.dumps({"error": f"Analysis failed: {info}"}))
        sys.exit(1)

    info_db = DISEASE_INFO.get(label, DISEASE_INFO["Healthy"])

    try:
        sys.stderr.close()
        sys.stderr = _orig_stderr
    except Exception:
        pass

    print(json.dumps({
        "status":      "healthy" if label == "Healthy" else "unhealthy",
        "disease":     label if label != "Healthy" else None,
        "confidence":  info,
        "description": info_db["description"],
        "solution":    info_db["solution"],
        "severity":    info_db["severity"],
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        try:
            sys.stderr.close()
            sys.stderr = _orig_stderr
        except Exception:
            pass
        print(json.dumps({
            "error":     f"Unexpected error: {e}",
            "traceback": traceback.format_exc()
        }))
        sys.exit(1)