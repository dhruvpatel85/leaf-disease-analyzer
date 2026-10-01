<?php
require_once '../config/db.php';

// Redirect if not logged in
if (!isset($_SESSION["user_id"])) {
    header("Location: ../auth/login.php");
    exit;
}

$user_name = $_SESSION["user_name"];
$user_id   = (int) $_SESSION["user_id"];

// Fetch analysis history (last 10)
$stmt = $conn->prepare(
    "SELECT * FROM analysis_history WHERE user_id = ? ORDER BY analyzed_at DESC LIMIT 10"
);
$stmt->bind_param("i", $user_id);
$stmt->execute();
$history = $stmt->get_result();
$history_rows = $history->fetch_all(MYSQLI_ASSOC);
$stmt->close();
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Leaf Analyzer</title>
    <link rel="stylesheet" href="../assets/css/style.css">
</head>
<body>

    <!-- Navigation -->
    <nav class="navbar">
        <div class="nav-brand">
            <span class="leaf-icon">🍃</span>
            <span>Leaf Analyzer</span>
        </div>
        <div class="nav-links">
            <span class="nav-user">👋 <?= htmlspecialchars($user_name) ?></span>
            <a href="../auth/logout.php" class="btn btn-outline">Logout</a>
        </div>
    </nav>

    <!-- Main Content -->
    <main class="dashboard">

        <!-- Upload Section -->
        <section class="upload-section">
            <h2>Analyze Leaf</h2>
            <p>Upload a photo of a leaf to detect diseases instantly</p>

            <div class="upload-area" id="uploadArea">
                <div class="upload-placeholder" id="uploadPlaceholder">
                    <span class="upload-icon">📤</span>
                    <p><strong>Drag &amp; drop</strong> your leaf image here</p>
                    <p class="upload-hint">or click to browse &nbsp;·&nbsp; JPG / PNG &nbsp;·&nbsp; max 5 MB</p>
                </div>
                <img id="previewImage" class="preview-image hidden" alt="Leaf Preview">
                <input type="file" id="fileInput" accept="image/jpeg,image/png,image/jpg" hidden>
            </div>

            <!-- Error box (shown by JS) -->
            <div id="jsErrorBox" class="alert alert-error" style="display:none; margin-top:12px;"></div>

            <div class="btn-group">
                <button id="analyzeBtn" class="btn btn-primary btn-lg" disabled>
                    🔍 Analyze Leaf
                </button>
                <button id="resetBtn" class="btn btn-outline btn-lg">
                    ↻ Reset
                </button>
            </div>
        </section>

        <!-- Loading Spinner -->
        <div class="loading hidden" id="loading">
            <div class="spinner"></div>
            <p>Analyzing leaf… Please wait</p>
        </div>

        <!-- Result Section -->
        <section class="result-section hidden" id="resultSection">
            <h2>Analysis Result</h2>
            <div class="result-card" id="resultCard">

                <div class="result-header">
                    <span class="result-icon" id="resultIcon"></span>
                    <div>
                        <h3 id="resultStatus"></h3>
                        <span class="severity-badge hidden" id="severityBadge"></span>
                    </div>
                </div>

                <div class="result-details">

                    <!-- Disease name (hidden for healthy) -->
                    <div class="result-item hidden" id="diseaseRow">
                        <strong>Disease Detected:</strong>
                        <span id="diseaseName"></span>
                    </div>

                    <!-- Description -->
                    <div class="result-item" id="descriptionRow">
                        <strong>About:</strong>
                        <p id="descriptionText"></p>
                    </div>

                    <!-- Confidence -->
                    <div class="result-item">
                        <strong>Confidence:</strong>
                        <span id="confidenceValue"></span>
                        <div class="confidence-bar">
                            <div class="confidence-fill" id="confidenceFill" style="width:0%"></div>
                        </div>
                    </div>

                    <!-- Solution -->
                    <div class="result-item">
                        <strong>💡 Recommended Actions:</strong>
                        <p id="solutionText" class="solution-text"></p>
                    </div>

                </div>
            </div>
        </section>

        <!-- History Section -->
        <section class="history-section">
            <h2>Recent Analysis History</h2>
            <div id="historyContainer">
                <?php if (count($history_rows) > 0): ?>
                    <div class="history-table-wrapper">
                        <table class="history-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Image</th>
                                    <th>Status</th>
                                    <th>Disease</th>
                                    <th>Confidence</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody id="historyBody">
                                <?php foreach ($history_rows as $i => $row): ?>
                                    <tr>
                                        <td><?= $i + 1 ?></td>
                                        <td>
                                            <img src="../<?= htmlspecialchars($row['image_path']) ?>"
                                                 class="history-thumb" alt="Leaf"
                                                 onerror="this.style.display='none'">
                                        </td>
                                        <td>
                                            <span class="badge <?= $row['result_status'] === 'healthy' ? 'badge-healthy' : 'badge-unhealthy' ?>">
                                                <?= ucfirst(htmlspecialchars($row['result_status'])) ?>
                                            </span>
                                        </td>
                                        <td><?= $row['disease_name'] ? htmlspecialchars($row['disease_name']) : '—' ?></td>
                                        <td><?= $row['confidence'] !== null ? round($row['confidence'], 1) . '%' : '—' ?></td>
                                        <td><?= date('M d, Y g:i A', strtotime($row['analyzed_at'])) ?></td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    </div>
                <?php else: ?>
                    <div class="empty-state" id="emptyState">
                        <span style="font-size:2.5rem;">🍃</span>
                        <p>No analysis history yet.</p>
                        <p>Upload a leaf image above to get started!</p>
                    </div>
                <?php endif; ?>
            </div>
        </section>

    </main>

    <!-- Pass PHP data to JS safely -->
    <script>
        // Existing history row count — used by JS to decide whether to build table or add to it
        window.LEAF_HISTORY_COUNT = <?= count($history_rows) ?>;
    </script>
    <script src="../assets/js/dashboard.js"></script>
</body>
</html>