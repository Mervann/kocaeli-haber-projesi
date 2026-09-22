/**
 * filters.js – Filter panel logic
 */

function getActiveFilters() {
    // News types
    const typeCheckboxes = document.querySelectorAll("#type-filters input[type=checkbox]");
    const activeTypes = [];
    typeCheckboxes.forEach((cb) => {
        if (cb.checked) activeTypes.push(cb.value);
    });

    // District
    const district = document.getElementById("district-filter").value;

    // Dates
    const dateFrom = document.getElementById("date-from").value;
    const dateTo = document.getElementById("date-to").value;

    return { types: activeTypes, district, dateFrom, dateTo };
}

function applyFilters() {
    const filters = getActiveFilters();
    filterAndDisplayNews(filters);
}

function resetFilters() {
    // Reset checkboxes
    document.querySelectorAll("#type-filters input[type=checkbox]").forEach((cb) => {
        cb.checked = true;
    });

    // Reset district
    document.getElementById("district-filter").value = "";

    // Reset dates
    document.getElementById("date-from").value = "";
    document.getElementById("date-to").value = "";

    // Reapply
    applyFilters();
}

function populateDistrictFilter(districts) {
    const select = document.getElementById("district-filter");
    // Keep first option
    select.innerHTML = '<option value="">Tüm İlçeler</option>';
    districts.forEach((d) => {
        if (d) {
            const opt = document.createElement("option");
            opt.value = d;
            opt.textContent = d;
            select.appendChild(opt);
        }
    });
}

function updateTypeCounts(newsItems) {
    const counts = {
        "Trafik Kazası": 0,
        "Yangın": 0,
        "Elektrik Kesintisi": 0,
        "Hırsızlık": 0,
        "Kültürel Etkinlikler": 0,
    };

    newsItems.forEach((n) => {
        if (counts[n.news_type] !== undefined) {
            counts[n.news_type]++;
        }
    });

    document.getElementById("count-trafik").textContent = counts["Trafik Kazası"];
    document.getElementById("count-yangin").textContent = counts["Yangın"];
    document.getElementById("count-elektrik").textContent = counts["Elektrik Kesintisi"];
    document.getElementById("count-hirsizlik").textContent = counts["Hırsızlık"];
    document.getElementById("count-kultur").textContent = counts["Kültürel Etkinlikler"];
}

// Setup real-time filter listeners
function setupFilterListeners() {
    // Checkbox changes
    document.querySelectorAll("#type-filters input[type=checkbox]").forEach((cb) => {
        cb.addEventListener("change", () => applyFilters());
    });

    // District change
    document.getElementById("district-filter").addEventListener("change", () => applyFilters());

    // Date changes
    document.getElementById("date-from").addEventListener("change", () => applyFilters());
    document.getElementById("date-to").addEventListener("change", () => applyFilters());
}
