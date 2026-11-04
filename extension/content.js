// ContextOS Browser Extension - Content Script
// Injected into web pages to enable selection saving and page content extraction.

// Listen for messages from the background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "get_page_content") {
    const content = extractPageContent();
    sendResponse(content);
  }
  if (message.action === "get_selection") {
    const selection = window.getSelection()?.toString() || "";
    sendResponse({ text: selection });
  }
});

// Extract meaningful content from the page
function extractPageContent() {
  const title = document.title;
  const url = window.location.href;
  const description =
    document.querySelector('meta[name="description"]')?.content || "";
  const author = document.querySelector('meta[name="author"]')?.content || "";
  const publishDate =
    document.querySelector('meta[property="article:published_time"]')
      ?.content ||
    document.querySelector('time[datetime]')?.getAttribute("datetime") ||
    "";

  // Try to extract main content
  const selectors = [
    "article",
    '[role="main"]',
    "main",
    ".post-content",
    ".article-body",
    ".entry-content",
    "#content",
  ];

  let mainContent = "";
  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) {
      mainContent = el.innerText;
      break;
    }
  }

  if (!mainContent) {
    mainContent = document.body.innerText;
  }

  // Truncate to reasonable size
  mainContent = mainContent.substring(0, 50000);

  return {
    title,
    url,
    description,
    author,
    publishDate,
    content: mainContent,
    timestamp: new Date().toISOString(),
  };
}
