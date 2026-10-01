<?php
// Buffer ALL output first — prevents any warning/notice from corrupting JSON
ob_start();

require_once '../config/db.php';

// Set JSON content-type header
header('Content-Type: application/json');

// ── Auth guard ─────────────────────────────────────────────────────────────
if (!isset($_SESSION["user_id"])) {
    ob_end_clean();
    echo json_encode(["success" => false, "message" => "Unauthorized. Please log in."]);
    exit;
}

// ── File upload validation ─────────────────────────────────────────────────
if (!isset($_FILES["leaf_image"]) || $_FILES["leaf_image"]["error"] !== UPLOAD_ERR_OK) {
    $upload_errors = [
        UPLOAD_ERR_INI_SIZE   => "File exceeds server upload limit (upload_max_filesize in php.ini).",
        UPLOAD_ERR_FORM_SIZE  => "File exceeds form size limit.",
        UPLOAD_ERR_PARTIAL    => "File was only partially uploaded.",
        UPLOAD_ERR_NO_FILE    => "No file was uploaded.",
        UPLOAD_ERR_NO_TMP_DIR => "Missing temp folder.",
        UPLOAD_ERR_CANT_WRITE => "Failed to write file to disk.",
        UPLOAD_ERR_EXTENSION  => "Upload blocked by PHP extension.",
    ];
    $err_code = $_FILES["leaf_image"]["error"] ?? UPLOAD_ERR_NO_FILE;
    ob_end_clean();
    echo json_encode([
        "success" => false,
        "message" => $upload_errors[$err_code] ?? "Upload error code: $err_code"
    ]);
    exit;
}

$file          = $_FILES["leaf_image"];
$allowed_types = ["image/jpeg", "image/png", "image/jpg"];
$max_size      = 5 * 1024 * 1024; // 5 MB

// ── Real MIME type check (don't trust browser-supplied type) ───────────────
$finfo     = finfo_open(FILEINFO_MIME_TYPE);
$real_mime = finfo_file($finfo, $file["tmp_name"]);
finfo_close($finfo);

if (!in_array($real_mime, $allowed_types)) {
    ob_end_clean();
    echo json_encode(["success" => false, "message" => "Only JPG and PNG images are allowed. Detected: $real_mime"]);
    exit;
}
if ($file["size"] > $max_size) {
    ob_end_clean();
    echo json_encode(["success" => false, "message" => "File size must be under 5 MB."]);
    exit;
}

// ── Save uploaded file ─────────────────────────────────────────────────────
$upload_dir = dirname(__DIR__) . '/uploads/';
if (!is_dir($upload_dir)) {
    mkdir($upload_dir, 0755, true);
}

$ext_map      = ["image/jpeg" => "jpg", "image/png" => "png", "image/jpg" => "jpg"];
$file_ext     = $ext_map[$real_mime] ?? 'jpg';
$new_filename = "leaf_" . time() . "_" . bin2hex(random_bytes(4)) . "." . $file_ext;
$file_path    = $upload_dir . $new_filename;

if (!move_uploaded_file($file["tmp_name"], $file_path)) {
    ob_end_clean();
    echo json_encode(["success" => false, "message" => "Failed to save image. Check uploads/ folder permissions."]);
    exit;
}

// ── Find Python 3 that has Pillow installed ────────────────────────────────
function findPython(): ?string {
    // All possible Python 3 locations on macOS (Homebrew Intel, Apple Silicon, system, pyenv, conda)
    $candidates = [
        '/opt/homebrew/bin/python3',        // Homebrew Apple Silicon (M1/M2/M3)
        '/opt/homebrew/bin/python3.12',
        '/opt/homebrew/bin/python3.11',
        '/opt/homebrew/bin/python3.10',
        '/usr/local/bin/python3',           // Homebrew Intel Mac
        '/usr/local/bin/python3.12',
        '/usr/local/bin/python3.11',
        '/usr/local/bin/python3.10',
        '/usr/bin/python3',                 // macOS system Python
        // pyenv
        $_SERVER['HOME'] . '/.pyenv/shims/python3',
        // conda
        $_SERVER['HOME'] . '/opt/anaconda3/bin/python3',
        $_SERVER['HOME'] . '/opt/miniconda3/bin/python3',
        $_SERVER['HOME'] . '/anaconda3/bin/python3',
        $_SERVER['HOME'] . '/miniconda3/bin/python3',
    ];

    // 1. Find the first Python that actually has Pillow
    foreach ($candidates as $path) {
        if (!is_executable($path)) continue;
        $check = shell_exec(escapeshellarg($path) . ' -c "import PIL; print(PIL.__version__)" 2>/dev/null');
        if ($check && trim($check) !== '') {
            return $path; // This Python has Pillow ✅
        }
    }

    // 2. Try PATH-resolved python3 (might work if MAMP inherits env)
    $via_which = trim((string) shell_exec('which python3 2>/dev/null'));
    if ($via_which !== '') {
        $check = shell_exec(escapeshellarg($via_which) . ' -c "import PIL; print(PIL.__version__)" 2>/dev/null');
        if ($check && trim($check) !== '') {
            return $via_which;
        }
    }

    // 3. Fall back to any Python3 (analyze_leaf.py will try to pip install)
    foreach ($candidates as $path) {
        if (is_executable($path)) return $path;
    }
    if ($via_which !== '') return $via_which;

    return null;
}

$python_cmd = findPython();
if (!$python_cmd) {
    ob_end_clean();
    echo json_encode([
        "success" => false,
        "message" => "Python 3 not found on this Mac.\n\nFix: Open Terminal and run:\n  brew install python\n  pip3 install pillow"
    ]);
    exit;
}

// ── Locate Python analyzer script ──────────────────────────────────────────
$project_root      = dirname(__DIR__);
$script_candidates = [
    $project_root . '/python/analyze_leaf.py',
    $project_root . '/analyze_leaf.py',
];

$script_path = null;
foreach ($script_candidates as $candidate) {
    if (file_exists($candidate)) {
        $script_path = realpath($candidate);
        break;
    }
}

if (!$script_path) {
    ob_end_clean();
    echo json_encode([
        "success" => false,
        "message" => "Python analyzer script not found. Make sure analyze_leaf.py is in the python/ folder."
    ]);
    exit;
}

// ── Run Python script ──────────────────────────────────────────────────────
// Use the full Python path so MAMP's restricted env doesn't matter
$command = escapeshellarg($python_cmd)
         . ' ' . escapeshellarg($script_path)
         . ' ' . escapeshellarg($file_path)
         . ' 2>&1';

exec($command, $output_array, $return_var);
$raw_output = implode("\n", $output_array);

// Extract JSON (ignore any stray lines before/after the JSON object)
$json_start = strpos($raw_output, '{');
$json_end   = strrpos($raw_output, '}');

if ($json_start === false || $json_end === false) {
    error_log("[LeafAnalyzer] No JSON in Python output: " . $raw_output);
    ob_end_clean();
    echo json_encode([
        "success" => false,
        "message" => "Analysis failed — Python script did not return JSON.\n\nThis usually means Pillow is not installed for the Python found at:\n$python_cmd\n\nFix: Open Terminal and run:\n  $python_cmd -m pip install pillow",
        "debug"   => substr($raw_output, 0, 800)
    ]);
    exit;
}

$json_string = substr($raw_output, $json_start, $json_end - $json_start + 1);
$analysis    = json_decode($json_string, true);

if (!$analysis || isset($analysis['error'])) {
    $err_msg = $analysis['error'] ?? 'Unknown Python error';
    error_log("[LeafAnalyzer] Python error: $err_msg | Output: $raw_output");
    ob_end_clean();
    echo json_encode([
        "success" => false,
        "message" => "Analysis failed: $err_msg",
        "debug"   => substr($raw_output, 0, 800)
    ]);
    exit;
}

// ── Extract results ────────────────────────────────────────────────────────
$result_status = $analysis['status']      ?? 'unhealthy';
$disease_name  = $analysis['disease']     ?? null;
$solution      = $analysis['solution']    ?? 'No solution provided.';
$confidence    = $analysis['confidence']  ?? 0;
$description   = $analysis['description'] ?? '';
$severity      = $analysis['severity']    ?? 'Unknown';

if ($result_status === 'healthy') {
    $disease_name = null;
}

// ── Save to database ───────────────────────────────────────────────────────
$user_id       = (int) $_SESSION["user_id"];
$relative_path = "uploads/" . $new_filename;

$stmt = $conn->prepare(
    "INSERT INTO analysis_history
        (user_id, image_path, result_status, disease_name, confidence, solution)
     VALUES (?, ?, ?, ?, ?, ?)"
);
$stmt->bind_param("isssds",
    $user_id,
    $relative_path,
    $result_status,
    $disease_name,
    $confidence,
    $solution
);
$stmt->execute();
$stmt->close();

// ── Send JSON response ─────────────────────────────────────────────────────
ob_end_clean();
echo json_encode([
    "success"     => true,
    "status"      => $result_status,
    "disease"     => $disease_name,
    "confidence"  => round((float) $confidence, 1),
    "description" => $description,
    "solution"    => $solution,
    "severity"    => $severity,
    "image"       => $relative_path
]);