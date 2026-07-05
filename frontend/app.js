/**
 * PaisaLog Frontend App
 *
 * This script is shared across all HTML pages. It handles:
 * 1. Setting the base URL for the API.
 * 2. Rendering a mobile-friendly bottom navigation bar.
 * 3. Highlighting the active page in the navigation.
 */

// Auto-detects hostname to set the API base URL.
// For local development, it points to the FastAPI server on port 8000.
const API_BASE_URL = window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000'
  : `http://${window.location.hostname}:8000`;

/**
 * Renders the bottom navigation bar and highlights the current page.
 * The nav bar is injected at the end of the body.
 */
function renderNav() {
    // HTML for the bottom navigation bar.
    // Each link has a data-page attribute that matches its HTML file name.
    const navHTML = `
        <nav class="bottom-nav">
            <a href="index.html" class="nav-item" data-page="index.html">
                <span class="nav-icon">🏠</span>
                <span class="nav-label">Home</span>
            </a>
            <a href="transactions.html" class="nav-item" data-page="transactions.html">
                <span class="nav-icon">💸</span>
                <span class="nav-label">Txs</span>
            </a>
            <a href="log.html" class="nav-item" data-page="log.html">
                <span class="nav-icon">➕</span>
                <span class="nav-label">Log</span>
            </a>
            <a href="social.html" class="nav-item" data-page="social.html">
                <span class="nav-icon">👥</span>
                <span class="nav-label">Social</span>
            </a>
            <a href="people.html" class="nav-item" data-page="people.html">
                <span class="nav-icon">👤</span>
                <span class="nav-label">People</span>
            </a>
            <a href="balance.html" class="nav-item" data-page="balance.html">
                <span class="nav-icon">⚖️</span>
                <span class="nav-label">Balance</span>
            </a>
            <a href="reports.html" class="nav-item" data-page="reports.html">
                <span class="nav-icon">📊</span>
                <span class="nav-label">Reports</span>
            </a>
            <a href="settings.html" class="nav-item" data-page="settings.html">
                <span class="nav-icon">⚙️</span>
                <span class="nav-label">Settings</span>
            </a>
        </nav>
    `;

    // Add the navigation to the page
    document.body.insertAdjacentHTML('beforeend', navHTML);

    // Get the current page's file name (e.g., "index.html")
    const path = window.location.pathname;
    const currentPage = path.substring(path.lastIndexOf('/') + 1) || 'index.html';

    // Find the corresponding nav item and add the 'active' class
    const activeNavItem = document.querySelector(`.nav-item[data-page="${currentPage}"]`);
    if (activeNavItem) {
        activeNavItem.classList.add('active');
    }
}

// When the DOM is fully loaded, render the navigation.
document.addEventListener('DOMContentLoaded', renderNav);