// ContextOS Browser Extension - Popup Script

const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const savePageBtn = document.getElementById("savePageBtn");
const saveSelectionBtn = document.getElementById("saveSelectionBtn");
const saveUrlBtn = document.getElementById("saveUrlBtn");
const resultDiv = document.getElementById("result");
const apiKeyInput = document.getElementById("apiKey");

// Load saved API key
chrome.storage.local.get(["contextos_api_key"], (result) => {
  if (result.contextos_api_key) {
    apiKeyInput.value = result.contextos_api_key;
  }
});

// Save API key on change
apiKeyInput.addEventListener("change", () => {
  chrome.runtime.sendMessage({
    action: "set_api_key",
    key: apiKeyInput.value,
  });
});

// Check connection status
async function checkConnection() {
  chrome.runtime.sendMessage({ action: "check_connection" }, (response) => {
    if (response && response.connected) {
      statusDot.classList.add("connected");
      statusText.textContent = `Connected (v${response.version || "?"})`;
      statusText.classList.add("connected");
      savePageBtn.disabled = false;
      saveSelectionBtn.disabled = false;
      saveUrlBtn.disabled = false;
    } else {
      statusDot.classList.remove("connected");
      statusText.textContent = "Not connected — is ContextOS running?";
      statusText.classList.remove("connected");
    }
  });
}

// Show result message
function showResult(message, type) {
  resultDiv.textContent = message;
  resultDiv.className = `result ${type}`;
  setTimeout(() => {
    resultDiv.className = "result";
  }, 3000);
}

// Save current page
savePageBtn.addEventListener("click", () => {
  savePageBtn.disabled = true;
  savePageBtn.textContent = "Saving...";

  chrome.runtime.sendMessage(
    { action: "save_current_page" },
    (response) => {
      savePageBtn.disabled = false;
      savePageBtn.innerHTML =
        '<span class="btn-icon">📄</span> Save This Page';

      if (response && response.success) {
        showResult("✓ Page saved to ContextOS", "success");
      } else {
        showResult(
          `✗ Failed: ${response?.error || "Unknown error"}`,
          "error"
        );
      }
    }
  );
});

// Save selection
saveSelectionBtn.addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    chrome.tabs.sendMessage(
      tabs[0].id,
      { action: "get_selection" },
      (response) => {
        if (response && response.text) {
          // Send selection to background
          chrome.runtime.sendMessage({
            action: "save_selection",
            text: response.text,
            tab: tabs[0],
          });
          showResult("✓ Selection saved to ContextOS", "success");
        } else {
          showResult("No text selected on the page", "error");
        }
      }
    );
  });
});

// Save URL only
saveUrlBtn.addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs[0];
    chrome.runtime.sendMessage({
      action: "save_link",
      url: tab.url,
      title: tab.title,
    });
    showResult("✓ URL saved to ContextOS", "success");
  });
});

// Open ContextOS Desktop tab
const openDesktopLink = document.getElementById("openDesktopLink");
if (openDesktopLink) {
  openDesktopLink.addEventListener("click", (e) => {
    e.preventDefault();
    chrome.tabs.create({ url: "http://127.0.0.1:1420" });
  });
}

// Check connection on popup open
checkConnection();
