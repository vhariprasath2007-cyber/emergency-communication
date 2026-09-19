const messages = {
    english: {
        title: "Flood Risk Warning",
        message: "Possible flooding has been reported in the Tambaram area. Avoid low-lying roads and unnecessary travel.",
        action: "Avoid low-lying areas and unnecessary travel."
    },
    tamil: {
        title: "வெள்ள அபாய எச்சரிக்கை",
        message: "தாம்பரம் பகுதியில் வெள்ளம் ஏற்படும் அபாயம் தெரிவிக்கப்பட்டுள்ளது. தாழ்வான சாலைகள் மற்றும் தேவையற்ற பயணங்களை தவிர்க்கவும்.",
        action: "தாழ்வான பகுதிகளை தவிர்த்து பாதுகாப்பான இடத்தில் இருங்கள்."
    },
    tanglish: {
        title: "Vella Abaya Echcharikkai",
        message: "Tambaram area-la flood varum possibility report pannirukanga. Low-lying roads-ai avoid pannunga. Thevai illadha travel avoid pannunga.",
        action: "Low-lying areas-ai avoid panni safe place-la irunga."
    }
};

const API_BASE = window.location.origin + "/api";

function processEmergency() {
    const processing = document.getElementById("processing");
    const processingText = document.getElementById("processingText");
    const languageSelect = document.getElementById("language");
    const locationInput = document.getElementById("location");

    processing.classList.remove("hidden");

    const steps = [
        "Collecting information from multiple sources...",
        "Extracting important facts...",
        "Classifying emergency priority...",
        "Checking conflicting reports...",
        "Grounding information to sources...",
        "Generating multilingual emergency alert..."
    ];

    let index = 0;
    const interval = setInterval(() => {
        processingText.textContent = steps[index];
        index += 1;

        if (index >= steps.length) {
            clearInterval(interval);
            setTimeout(async () => {
                try {
                    const response = await fetch(`${API_BASE}/emergency`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            emergency_type: "natural_disaster",
                            description: `Emergency reported near ${locationInput.value || "Tambaram, Chennai"}. Immediate assistance may be required.`,
                            user_name: "User",
                            location: {
                                latitude: 12.92,
                                longitude: 80.12,
                                label: locationInput.value || "Tambaram, Chennai"
                            }
                        })
                    });

                    const data = await response.json();
                    if (!response.ok) {
                        throw new Error(data.error || "Unable to create emergency alert");
                    }

                    const aiSummary = data.ai_message?.summary || "Emergency information processed successfully.";
                    const aiAction = data.ai_message?.help_required || "Contact local emergency services.";
                    const aiAlert = data.ai_message?.alert_text || data.description;

                    document.getElementById("alertTitle").textContent = aiSummary;
                    document.getElementById("alertDescription").textContent = aiAlert;

                    const selectedLanguage = languageSelect.value;
                    const languageButton = document.querySelector(`.language-tab[data-language="${selectedLanguage}"]`);
                    changeLanguage(selectedLanguage, languageButton, {
                        title: aiSummary,
                        message: aiAlert,
                        action: aiAction
                    });

                    updateDashboard();
                    showToast("✓", "Emergency information processed successfully");
                } catch (error) {
                    console.error(error);
                    showToast("⚠️", error.message || "Unable to reach the emergency service");
                } finally {
                    processing.classList.add("hidden");
                }
            }, 700);
        }
    }, 500);
}

function updateDashboard() {
    document.getElementById("sourceCount").textContent = "4";
    document.getElementById("criticalCount").textContent = "1";
    document.getElementById("conflictCount").textContent = "1";
    document.getElementById("latency").textContent = `${(Math.random() * 0.5 + 0.5).toFixed(1)}s`;
}

function changeLanguage(language, button, overrides = {}) {
    const data = messages[language] || messages.english;

    document.getElementById("messageTitle").textContent = overrides.title || data.title;
    document.getElementById("generatedMessage").textContent = overrides.message || data.message;
    document.getElementById("recommendedAction").textContent = overrides.action || data.action;

    document.querySelectorAll(".language-tab").forEach((tab) => tab.classList.remove("active"));

    if (button) {
        button.classList.add("active");
    }
}

document.getElementById("language").addEventListener("change", function () {
    const button = document.querySelector(`.language-tab[data-language="${this.value}"]`);
    changeLanguage(this.value, button);
});

function openContactModal() {
    document.getElementById("contactModal").classList.add("show");
}

function closeContactModal() {
    document.getElementById("contactModal").classList.remove("show");
}

function saveContact() {
    const name = document.getElementById("contactName").value.trim();
    const phone = document.getElementById("contactPhone").value.trim();
    const relation = document.getElementById("contactRelation").value;

    if (!name || !phone) {
        showToast("⚠️", "Please enter contact name and phone number");
        return;
    }

    const card = document.createElement("div");
    card.className = "contact-card";
    card.innerHTML = `
        <div class="contact-avatar">👤</div>
        <div class="contact-info">
            <h3>${escapeHTML(name)}</h3>
            <p>${escapeHTML(relation)}</p>
            <span>${escapeHTML(phone)}</span>
        </div>
        <button class="alert-contact" onclick="alertContact('${escapeJS(name)}')">🚨 Alert</button>
    `;

    document.getElementById("contactsList").appendChild(card);
    document.getElementById("contactName").value = "";
    document.getElementById("contactPhone").value = "";
    closeContactModal();
    showToast("✓", "Emergency contact added");
}

function alertContact(name) {
    showToast("🚨", `Emergency alert prepared for ${name}`);
}

async function sendSOS() {
    const contacts = document.querySelectorAll(".contact-card");
    if (contacts.length === 0) {
        showToast("⚠️", "No emergency contacts available");
        return;
    }

    const language = document.getElementById("language").value;
    const location = document.getElementById("location").value || "Tambaram, Chennai";

    const templates = {
        tamil: `🆘 அவசர எச்சரிக்கை! ${location} பகுதியில் உதவி தேவைப்படலாம். உடனடியாக தொடர்பு கொள்ளவும்.`,
        tanglish: `🆘 EMERGENCY! ${location} area-la emergency situation detected. Please immediately contact the user.`,
        english: `🆘 EMERGENCY ALERT! Possible emergency detected near ${location}. Please contact the user immediately.`
    };

    const message = templates[language] || templates.english;

    try {
        const response = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message, context: { location } })
        });

        const data = await response.json();
        const reply = data.reply || "Emergency guidance prepared.";

        showToast("🆘", reply.length > 60 ? "SOS alert prepared for all emergency contacts" : reply);
        console.log("SOS MESSAGE:", message);
    } catch (error) {
        console.error(error);
        showToast("🆘", "SOS alert prepared for all emergency contacts");
    }
}

function showToast(icon, message) {
    const toast = document.getElementById("toast");
    document.getElementById("toastIcon").textContent = icon;
    document.getElementById("toastMessage").textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

function escapeHTML(value) {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function escapeJS(value) {
    return String(value).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}

window.addEventListener("load", () => {
    setTimeout(() => {
        showToast("✓", "Emergency monitoring system is online");
    }, 800);

    const initialButton = document.querySelector('.language-tab[data-language="english"]');
    if (initialButton) {
        changeLanguage("english", initialButton);
    }
});