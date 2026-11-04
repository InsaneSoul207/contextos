// ContextOS Browser Extension - Background Service Worker
// Handles context menus, communication with the desktop app, and queued saves.

const CONTEXTOS_API = "http://127.0.0.1:44480";
let apiKey = "";

// Load API key from storage
chrome.storage.local.get(["contextos_api_key"], (result) => {
  if (result.contextos_api_key) {
    apiKey = result.contextos_api_key;
  }
});

// Create context menu items
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "save-page",
    title: "Save Page to ContextOS",
    contexts: ["page"],
  });

  chrome.contextMenus.create({
    id: "save-selection",
    title: "Save Selection to ContextOS",
    contexts: ["selection"],
  });

  chrome.contextMenus.create({
    id: "save-link",
    title: "Save Link to ContextOS",
    contexts: ["link"],
  });

  chrome.contextMenus.create({
    id: "save-image",
    title: "Save Image to ContextOS",
    contexts: ["image"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  try {
    switch (info.menuItemId) {
      case "save-page":
        await savePage(tab);
        break;
      case "save-selection":
        await saveSelection(info.selectionText, tab);
        break;
      case "save-link":
        await saveLink(info.linkUrl, tab);
        break;
      case "save-image":
        await saveImage(info.srcUrl, tab);
        break;
    }
  } catch (error) {
    console.error("ContextOS save error:", error);
    notifyUser("Failed to save to ContextOS. Is the app running?", "error");
  }
});

// Save the full page
async function savePage(tab) {
  const content = await getPageContent(tab.id);
  const payload = {
    type: "webpage",
    title: tab.title || "Untitled Page",
    url: tab.url,
    content: content,
    timestamp: new Date().toISOString(),
    metadata: {
      favicon: tab.favIconUrl,
    },
  };
  await sendToContextOS(payload);
  notifyUser(`Saved: ${tab.title}`, "success");
}

// Save selected text
async function saveSelection(text, tab) {
  const payload = {
    type: "text_selection",
    title: `Selection from ${tab.title}`,
    url: tab.url,
    content: text,
    timestamp: new Date().toISOString(),
    metadata: {
      source_page: tab.title,
    },
  };
  await sendToContextOS(payload);
  notifyUser("Selection saved to ContextOS", "success");
}

// Save a link
async function saveLink(url, tab) {
  const payload = {
    type: "link",
    title: `Link from ${tab.title}`,
    url: url,
    content: url,
    timestamp: new Date().toISOString(),
    metadata: {
      source_page: tab.title,
      source_url: tab.url,
    },
  };
  await sendToContextOS(payload);
  notifyUser("Link saved to ContextOS", "success");
}

// Save an image
async function saveImage(imageUrl, tab) {
  const payload = {
    type: "image",
    title: `Image from ${tab.title}`,
    url: imageUrl,
    content: "",
    timestamp: new Date().toISOString(),
    metadata: {
      source_page: tab.title,
      source_url: tab.url,
      image_url: imageUrl,
    },
  };
  await sendToContextOS(payload);
  notifyUser("Image saved to ContextOS", "success");
}

// Get page content via content script
async function getPageContent(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        const article = document.querySelector("article") || document.body;
        return article.innerText.substring(0, 50000);
      },
    });
    return results[0]?.result || "";
  } catch {
    return "";
  }
}

// Send data to ContextOS backend
async function sendToContextOS(payload) {
  const response = await fetch(`${CONTEXTOS_API}/api/documents/capture`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`ContextOS API error: ${response.status} - ${error}`);
  }

  return response.json();
}

// Show notification
function notifyUser(message, type) {
  chrome.runtime.sendMessage({
    action: "notification",
    message,
    type,
  });
}

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "check_connection") {
    checkConnection().then(sendResponse);
    return true;
  }
  if (message.action === "set_api_key") {
    apiKey = message.key;
    chrome.storage.local.set({ contextos_api_key: message.key });
    sendResponse({ success: true });
  }
  if (message.action === "save_current_page") {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (tabs[0]) {
        try {
          await savePage(tabs[0]);
          sendResponse({ success: true });
        } catch (error) {
          sendResponse({ success: false, error: error.message });
        }
      }
    });
    return true;
  }
});

// Check connection to ContextOS
async function checkConnection() {
  try {
    const response = await fetch(`${CONTEXTOS_API}/health`);
    const data = await response.json();
    return { connected: true, version: data.version };
  } catch {
    return { connected: false };
  }
}
