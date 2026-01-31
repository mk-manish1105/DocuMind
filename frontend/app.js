/**
 * app.js
 *
 * Frontend controller for DocuMind.
 * Responsibilities:
 *  - Manage authentication (login / register / guest)
 *  - Maintain UI state (modal, sidebar, processing overlay)
 *  - Upload documents and show processing progress
 *  - Start/continue chat sessions, stream assistant responses
 *  - Load and render session history / documents
 *
 * Important notes:
 *  - This file manipulates DOM elements by id. If you rename an element in HTML,
 *    update the corresponding id usage here.
 *  - No business logic (API) changes are performed here — only client-side UI logic.
 *  - The API root is set by `API` constant — change to point to your deployed backend.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ------------------------
  // Configuration & State
  // ------------------------
  const API = "https://gmt-guided-wanting-oakland.trycloudflare.com";
    // backend root
  const TOKEN_KEY = "documind_token";     // localStorage key for JWT

  // Local runtime state
  let token = localStorage.getItem(TOKEN_KEY);
  let currentSession = null;
  let isGuest = false;
  let userEmail = localStorage.getItem("documind_email") || "";

  // Short helpers
  const qs = id => document.getElementById(id);

  /**
   * safeOn(id, event, fn)
   * - Registers event listener if element exists.
   * - Returns the element (or null) so callers can use it if needed.
   * - Prevents uncaught errors when DOM element is missing.
   */
  const safeOn = (id, event, fn) => {
    const el = qs(id);
    if (!el) {
      console.warn(`Missing element: #${id}`);
      return null;
    }
    el.addEventListener(event, fn);
    return el;
  };

  // Build Authorization headers for fetch calls when token is present
  function authHeaders() {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  // ------------------------
  // UI: Sidebar toggle
  // ------------------------
  safeOn("sidebarToggle", "click", () => {
    const sidebar = qs("sidebar");
    if (sidebar) {
      sidebar.classList.toggle("collapsed");
    }
  });

  // ------------------------
  // UI: Auto-resize textarea
  // ------------------------
  // Keep textarea height in sync with content, but cap at 200px
  const messageInput = qs("messageInput");
  if (messageInput) {
    messageInput.addEventListener("input", function() {
      this.style.height = "auto";
      this.style.height = Math.min(this.scrollHeight, 200) + "px";
    });
  }

  // ------------------------
  // Update user profile UI (sidebar)
  // ------------------------
  // If logged-in, show initials and a cleaned name from email. Hide profile for guests.
  function updateUserProfile(email) {
    const profile = qs("userProfile");
    const avatar = qs("userAvatar");
    const userName = qs("userName");
    
    if (!profile || !avatar || !userName) return;

    if (email && !isGuest) {
      const name = email.split("@")[0];
      // Create initials from first two segments (split on dot/underscore/hyphen)
      const initials = name.split(/[._-]/).map(part => part[0].toUpperCase()).join("").slice(0, 2);
      
      avatar.textContent = initials;
      // Make a readable display name from email local part
      userName.textContent = name.charAt(0).toUpperCase() + name.slice(1).replace(/[._-]/g, " ");
      profile.style.display = "flex";
    } else {
      profile.style.display = "none";
    }
  }

  // ------------------------
  // Processing overlay helpers
  // ------------------------
  // Show an unobtrusive bottom overlay while uploads/indexing happen.
  function showProcessingOverlay(message = "Uploading & indexing documents…") {
    const overlay = qs("processingOverlay");
    const msg = qs("overlayMessage");
    const details = qs("processingDetails");
    const progressBar = qs("progressBar");

    if (msg) msg.textContent = message;
    if (details) details.textContent = "Your chat history remains visible. Please wait while we process your files.";

    // Simulated progress animation — purely visual on client side
    if (progressBar) {
      progressBar.style.width = "0%";
      setTimeout(() => {
        progressBar.style.width = "70%"; // Simulated progress
      }, 100);
    }

    if (overlay && overlay.classList.contains("hidden")) {
      overlay.classList.remove("hidden");
      overlay.setAttribute("aria-hidden", "false");
    }

    // Disable upload controls and send button while keeping textarea visible
    const fi = qs("fileInput");
    const up = qs("uploadBtn");
    const msgInput = qs("messageInput");
    const sendBtn = qs("sendBtn");

    if (fi) fi.disabled = true;
    if (up) up.disabled = true;
    if (msgInput) {
      // Keep textarea enabled so user can read history and compose drafts
      msgInput.placeholder = "Uploading files… you can still type but sending is disabled.";
    }
    if (sendBtn) sendBtn.disabled = true;
  }

  // Hide overlay and re-enable controls. Small delay used to show completion.
  function hideProcessingOverlay() {
    const overlay = qs("processingOverlay");
    const progressBar = qs("progressBar");

    if (progressBar) {
      progressBar.style.width = "100%";
    }

    setTimeout(() => {
      if (overlay && !overlay.classList.contains("hidden")) {
        overlay.classList.add("hidden");
        overlay.setAttribute("aria-hidden", "true");
      }

      // Re-enable inputs depending on auth state
      const fi = qs("fileInput");
      const up = qs("uploadBtn");
      const msgInput = qs("messageInput");
      const sendBtn = qs("sendBtn");

      if (fi) fi.disabled = !token;
      if (up) up.disabled = !token;
      if (msgInput) {
        msgInput.placeholder = "Ask me anything...";
      }
      if (sendBtn) sendBtn.disabled = false;
    }, 400);
  }
  
  // ------------------------
  // Auth UI updates (Login vs Logout button)
  // ------------------------
  function updateAuthUI() {
    const logoutBtn = qs("logoutBtn");
    const loginModal = qs("loginModal");

    if (!logoutBtn) return;

    // If guest or no token -> show "Login" which opens the modal
    if (isGuest || !token) {
      logoutBtn.textContent = "Login";
      logoutBtn.onclick = () => {
        if (loginModal) {
          loginModal.classList.remove("hidden");
          loginModal.style.display = "flex";
        }
      };
    } else {
      // If logged in -> show "Logout" which clears local state and returns to modal
      logoutBtn.textContent = "Logout";
      logoutBtn.onclick = () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem("documind_email");
        token = null;
        isGuest = false;
        userEmail = "";

        const appDiv = qs("app");
        const loginModal = qs("loginModal");
        if (appDiv) appDiv.classList.add("hidden");
        if (loginModal) {
          loginModal.classList.remove("hidden");
          loginModal.style.display = "flex";
        }

        updateUserProfile("");
        updateDocsSection();
        updateAuthUI();
      };
    }
  }

  // ------------------------
  // LOGIN / REGISTER UI toggles
  // ------------------------
  safeOn("showRegister", "click", (e) => {
    e.preventDefault();
    const loginForm = qs("loginForm");
    const registerForm = qs("registerForm");
    if (loginForm) loginForm.style.display = "none";
    if (registerForm) registerForm.style.display = "block";

    // Clear any previous errors
    const loginError = qs("loginError");
    const registerError = qs("registerError");
    if (loginError) loginError.textContent = "";
    if (registerError) registerError.textContent = "";
  });

  safeOn("showLogin", "click", (e) => {
    e.preventDefault();
    const loginForm = qs("loginForm");
    const registerForm = qs("registerForm");
    if (loginForm) loginForm.style.display = "block";
    if (registerForm) registerForm.style.display = "none";

    // Clear any previous errors
    const loginError = qs("loginError");
    const registerError = qs("registerError");
    if (loginError) loginError.textContent = "";
    if (registerError) registerError.textContent = "";
  });

  // ------------------------
  // Login handler: POST /auth/login (OAuth2 Password grant)
  // ------------------------
  async function handleLogin() {
    const loginErrorEl = qs("loginError");
    if (loginErrorEl) loginErrorEl.textContent = "";

    const emailEl = qs("loginEmail");
    const passwordEl = qs("loginPassword");
    if (!emailEl || !passwordEl) {
      if (loginErrorEl) loginErrorEl.textContent = "Form inputs missing";
      return;
    }

    const email = emailEl.value.trim();
    const password = passwordEl.value.trim();

    if (!email || !password) {
      if (loginErrorEl) loginErrorEl.textContent = "Email and password are required";
      return;
    }

    try {
      const loginRes = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password: password })
      });

      if (!loginRes.ok) {
        const txt = await loginRes.text().catch(() => "");
        let msg = "Invalid email or password";

        try {
          const json = JSON.parse(txt);
          if (json && json.detail) {
            msg = typeof json.detail === "string" ? json.detail : "Invalid credentials";
          }
        } catch {}

        if (loginErrorEl) loginErrorEl.textContent = msg;
        return;
      }

      // Store token and email locally and initialize the app UI
      const data = await loginRes.json();
      token = data.access_token;
      userEmail = email;
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem("documind_email", email);
      isGuest = false;
      updateAuthUI();

      // Clear inputs
      emailEl.value = "";
      passwordEl.value = "";

      await initApp();

    } catch (err) {
      console.error("Login error", err);
      if (loginErrorEl) loginErrorEl.textContent = "Network error. Please try again.";
    }
  }

  // ------------------------
  // Register handler: POST /auth/register then auto-login
  // ------------------------
  async function handleRegister() {
    const registerErrorEl = qs("registerError");
    if (registerErrorEl) registerErrorEl.textContent = "";

    const emailEl = qs("registerEmail");
    const passwordEl = qs("registerPassword");
    const confirmPasswordEl = qs("registerConfirmPassword");

    if (!emailEl || !passwordEl || !confirmPasswordEl) {
      if (registerErrorEl) registerErrorEl.textContent = "Form inputs missing";
      return;
    }

    const email = emailEl.value.trim();
    const password = passwordEl.value.trim();
    const confirmPassword = confirmPasswordEl.value.trim();

    // Basic client-side validation
    if (!email || !password || !confirmPassword) {
      if (registerErrorEl) registerErrorEl.textContent = "All fields are required";
      return;
    }

    if (!email.includes("@")) {
      if (registerErrorEl) registerErrorEl.textContent = "Please enter a valid email";
      return;
    }

    if (password.length < 6) {
      if (registerErrorEl) registerErrorEl.textContent = "Password must be at least 6 characters";
      return;
    }

    if (password !== confirmPassword) {
      if (registerErrorEl) registerErrorEl.textContent = "Passwords do not match";
      return;
    }

    try {
      // Create account
      const regRes = await fetch(`${API}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: "" })
      });

      if (!regRes.ok) {
        const txt = await regRes.text().catch(() => "");
        let msg = "Registration failed";

        try {
          const json = JSON.parse(txt);
          if (json && json.detail) {
            msg = typeof json.detail === "string" ? json.detail : "Registration failed";
          }
        } catch {}

        if (registerErrorEl) registerErrorEl.textContent = msg;
        return;
      }

      // Auto-login after successful registration (keeps UX smooth)
      const loginRes = await fetch(`${API}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password: password })
      });

      if (!loginRes.ok) {
        if (registerErrorEl) {
          registerErrorEl.textContent = "Account created! Please login manually.";
        }
        // Switch to login form after a short delay
        setTimeout(() => {
          qs("showLogin") && qs("showLogin").click();
        }, 2000);
        return;
      }

      const data = await loginRes.json();
      token = data.access_token;
      userEmail = email;
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem("documind_email", email);
      isGuest = false;
      updateAuthUI();

      // Clear inputs
      emailEl.value = "";
      passwordEl.value = "";
      confirmPasswordEl.value = "";

      await initApp();

    } catch (err) {
      console.error("Registration error", err);
      if (registerErrorEl) registerErrorEl.textContent = "Network error. Please try again.";
    }
  }

  // Attach login/register handlers to buttons
  safeOn("loginBtn", "click", handleLogin);
  safeOn("registerBtn", "click", handleRegister);

  // Keyboard: Enter to submit forms (login & register)
  const loginEmail = qs("loginEmail");
  const loginPassword = qs("loginPassword");
  if (loginEmail) {
    loginEmail.addEventListener("keydown", e => {
      if (e.key === "Enter") handleLogin();
    });
  }
  if (loginPassword) {
    loginPassword.addEventListener("keydown", e => {
      if (e.key === "Enter") handleLogin();
    });
  }

  const registerEmail = qs("registerEmail");
  const registerPassword = qs("registerPassword");
  const registerConfirmPassword = qs("registerConfirmPassword");
  if (registerEmail) {
    registerEmail.addEventListener("keydown", e => {
      if (e.key === "Enter") handleRegister();
    });
  }
  if (registerPassword) {
    registerPassword.addEventListener("keydown", e => {
      if (e.key === "Enter") handleRegister();
    });
  }
  if (registerConfirmPassword) {
    registerConfirmPassword.addEventListener("keydown", e => {
      if (e.key === "Enter") handleRegister();
    });
  }

  // ------------------------
  // Continue as Guest
  // ------------------------
  // Guests can chat using general knowledge only; uploads & document-based answers disabled.
  safeOn("guestBtn", "click", () => {
    isGuest = true;
    token = null;
    userEmail = "";
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("documind_email");

    const loginModal = qs("loginModal");
    const appDiv = qs("app");
    if (loginModal) loginModal.classList.add("hidden");
    if (appDiv) {
      appDiv.classList.remove("hidden");
      appDiv.style.display = "flex";
    }

    currentSession = null;
    const chat = qs("chat");
    if (chat) chat.innerHTML = "";

    updateUserProfile("");
    updateDocsSection();
    updateAuthUI();
  });

  // ------------------------
  // New chat / reset chat UI
  // ------------------------
  safeOn("newChatBtn", "click", () => {
    currentSession = null;
    const chat = qs("chat");
    if (chat) chat.innerHTML = "";

    appendSystem("🆕 New chat started");

    // Clear active state from session list
    const sessionList = qs("sessionList");
    if (sessionList) {
      [...sessionList.children].forEach(li => li.classList.remove("active"));
    }
  });

  // ------------------------
  // App initialization (after login)
  // ------------------------
  async function initApp() {
    const loginModal = qs("loginModal");
    const appDiv = qs("app");

    if (loginModal) loginModal.classList.add("hidden");
    if (appDiv) {
      appDiv.classList.remove("hidden");
      appDiv.style.display = "flex";
    }

    isGuest = false;
    updateUserProfile(userEmail);
    await loadSessions();
    await loadDocuments();
    updateDocsSection();
  }

  // If token exists from a previous session, initialize automatically
  if (token) {
    userEmail = localStorage.getItem("documind_email") || "";
    isGuest = false;
    initApp();
    updateAuthUI();
  }
  
  // ------------------------
  // Load user chat sessions (sidebar)
  // ------------------------
  async function loadSessions() {
    const sl = qs("sessionList");
    if (!sl) return;

    if (!token) {
      sl.innerHTML = "";
      return;
    }

    try {
      console.log("[Sessions] fetching sessions from", `${API}/chat/sessions`);
      const res = await fetch(`${API}/chat/sessions`, { headers: { ...authHeaders() }});
      if (!res.ok) {
        console.warn("[Sessions] server returned", res.status);
        sl.innerHTML = "";
        return;
      }

      const sessions = await res.json();
      if (!Array.isArray(sessions)) {
        console.warn("[Sessions] unexpected sessions payload:", sessions);
        sl.innerHTML = "";
        return;
      }

      sl.innerHTML = "";

      sessions.forEach(s => {
        const li = document.createElement("li");

        // Support a variety of session id shapes just in case the backend differs
        const sid = s.id ?? s.session_id ?? s.sessionId ?? null;
        li.dataset.sessionId = sid;
      
        if (sid && currentSession && Number(sid) === Number(currentSession)) {
          li.classList.add("active");
        }
    
        const created = s.created_at ?? s.createdAt ?? s.created ?? null;
        li.textContent = s.title || "New chat";

        li.addEventListener("click", () => {
          [...sl.children].forEach(x => x.classList.remove("active"));
          li.classList.add("active");
          const idToLoad = li.dataset.sessionId;
          console.log("[Sessions] clicked session id:", idToLoad);
          if (!idToLoad) {
            appendSystem("Cannot load this session (missing id).");
            return;
          }
          loadHistory(idToLoad);
        });

        sl.appendChild(li);
      });

      console.log("[Sessions] loaded", sessions.length, "sessions");
    } catch (err) {
      console.error("loadSessions error", err);
      sl.innerHTML = "";
    }
  }

  // ------------------------
  // Load chat history for a given session id
  // ------------------------
  async function loadHistory(id) {
    console.log("[History] loadHistory called with id:", id);
    currentSession = id;
    const chat = qs("chat");
    if (chat) chat.innerHTML = "";

    // Temporarily hide overlay if it's visible to avoid visual overlap while loading
    const overlay = qs("processingOverlay");
    let overlayWasVisible = false;
    if (overlay) {
      overlayWasVisible = !overlay.classList.contains("hidden");
      if (overlayWasVisible) {
        overlay.style.visibility = "hidden";
        overlay.style.pointerEvents = "none";
      }
    }

    if (!token) {
      appendSystem("Guest sessions have no history.");
      if (overlay && overlayWasVisible) {
        overlay.style.visibility = "";
        overlay.style.pointerEvents = "";
      }
      return;
    }

    try {
      const url = `${API}/chat/history/${encodeURIComponent(id)}`;
      console.log("[History] fetching", url);
      const res = await fetch(url, { headers: { ...authHeaders() }});
      if (!res.ok) {
        const bodyText = await res.text().catch(()=>"");
        console.warn("[History] server returned", res.status, bodyText);
        appendSystem("Cannot load history. Server error: " + res.status);
        return;
      }

      const msgs = await res.json();
      if (!Array.isArray(msgs)) {
        console.warn("[History] unexpected history payload:", msgs);
        appendSystem("No history found for this session.");
        return;
      }

      if (msgs.length === 0) {
        appendSystem("No messages in this session.");
        return;
      }

      // Append messages in order — detect role shape and normalize to "user" / "bot"
      msgs.forEach(m => {
        const content = m.content ?? m.text ?? m.message ?? m.body ?? "";
        const roleRaw = (m.role ?? m.sender ?? "").toString().toLowerCase();
        const role = roleRaw.includes("user") || roleRaw.includes("me") ? "user" : "bot";

        appendMessage(content, role);
      });

      console.log("[History] appended", msgs.length, "messages");
    } catch (err) {
      console.error("loadHistory error", err);
      appendSystem("Failed to load history.");
    } finally {
      // Restore overlay visibility if it was visible before
      if (overlay && overlayWasVisible) {
        setTimeout(() => {
          overlay.style.visibility = "";
          overlay.style.pointerEvents = "";
        }, 80);
      }
    }
  }

  // ------------------------
  // Markdown + code rendering helper
  // ------------------------
  // Converts markdown to HTML (uses `marked` if present).
  // Additionally wraps code blocks with a copy button and code-block container.
  function renderMessageWithCode(text) {
    if (!window.marked) {
      return text;
    }

    marked.setOptions({
      breaks: true,
      gfm: true,
    });

    let html = marked.parse(text);

    // Replace standard <pre><code class="language-x"> blocks with a code block UI
    html = html.replace(/<pre><code class="language-(\w*)">([\s\S]*?)<\/code><\/pre>/g,
      (_, lang, code) => {
        return `
          <div class="code-block">
            <button class="copy-btn">Copy</button>
            <pre><code class="language-${lang}">${code}</code></pre>
          </div>
        `;
      }
    );

    return html;
  }

  // ------------------------
  // Append helpers for messages
  // ------------------------
  function appendMessage(text, role) {
    const div = document.createElement("div");
    div.className = `msg ${role}`;
    div.innerHTML = renderMessageWithCode(text);
    const chat = qs("chat");
    if (chat) {
      chat.appendChild(div);
      const wrapper = qs("chatWrapper");
      if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
    }
  }

  // System / helper messages (styled as bot but italic)
  function appendSystem(text) {
    const div = document.createElement("div");
    div.className = `msg bot`;
    div.style.fontStyle = "italic";
    div.style.opacity = "0.8";
    div.textContent = text;
    const chat = qs("chat");
    if (chat) {
      chat.appendChild(div);
      const wrapper = qs("chatWrapper");
      if (wrapper) wrapper.scrollTop = wrapper.scrollHeight;
    }
  }

  // ------------------------
  // Send message (main chat flow)
  // - POST /chat with question, optional session_id
  // - If response is streamed, read the stream and append incrementally
  // ------------------------
  safeOn("sendBtn", "click", sendMessage);
  if (messageInput) {
    messageInput.addEventListener("keydown", e => {
      // Enter (without Shift) sends the message
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  async function sendMessage() {
    const input = qs("messageInput");
    if (!input) return;
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    input.style.height = "auto";
    appendMessage(question, "user");

    const headers = { "Content-Type": "application/json", ...authHeaders() };

    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          question,
          session_id: currentSession,
          max_tokens: 1600
        })
      });

      if (!res.ok) {
        const txt = await res.text().catch(()=>"");
        appendSystem("Server error: " + (txt || res.status));
        return;
      }

      // Check for X-Session-Id header (backend may create a new session)
      const sid = res.headers.get("X-Session-Id");
      if (sid) {
        const parsed = Number(sid);
        if (!isNaN(parsed)) {
          currentSession = parsed;
          console.log("[Chat] session ID:", currentSession);
          
          // Update active session in sidebar (if present)
          const sessionList = qs("sessionList");
          if (sessionList && token) {
            [...sessionList.children].forEach(li => {
              li.classList.remove("active");
              if (li.dataset.sessionId === String(currentSession)) {
                li.classList.add("active");
              }
            });
          }
        }
      }

      // If not streaming body, treat entire response as final message
      if (!res.body) {
        const text = await res.text();
        appendMessage(text, "bot");
        if (token) await loadSessions();
        return;
      }

      // Streamed response handling (reads NDJSON-style lines)
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let botText = "";
      const botDiv = document.createElement("div");
      botDiv.className = "msg bot";
      qs("chat") && qs("chat").appendChild(botDiv);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        chunk.split("\n").forEach(line => {
          if (!line.trim()) return;
          try {
            const data = JSON.parse(line);
            if (data.content) {
              botText += data.content;
              botDiv.innerHTML = renderMessageWithCode(botText);
            }
          } catch (err) { /* ignore parse errors */ }
        });
      }

      // After finishing, refresh sessions if authenticated
      if (token) await loadSessions();

    } catch (err) {
      console.error("sendMessage error", err);
      appendSystem(
        "⚠️ The backend is currently paused to optimize cloud resource usage. " +
        "This project is actively maintained and can be resumed on demand."
      );
    }
  }
s
  // ------------------------
  // Documents UI state / upload handler
  // ------------------------
  function updateDocsSection() {
    const hint = qs("docsHint");
    if (!hint) return;
    if (!token) {
      hint.textContent = "(login to manage)";
      qs("uploadBtn") && (qs("uploadBtn").disabled = true);
      qs("fileInput") && (qs("fileInput").disabled = true);
    } else {
      hint.textContent = "";
      qs("uploadBtn") && (qs("uploadBtn").disabled = false);
      qs("fileInput") && (qs("fileInput").disabled = false);
    }
  }

  // Upload button handler: posts files to /files/upload as multipart/form-data
  safeOn("uploadBtn", "click", async () => {
    if (!token) {
      alert("Login required to upload.");
      return;
    }

    const fileInput = qs("fileInput");
    const status = qs("uploadStatus");
    const details = qs("processingDetails");
    
    if (!fileInput || !status) return;

    const files = fileInput.files;
    if (!files || files.length === 0) {
      status.textContent = "Please select files first.";
      setTimeout(()=> status.textContent = "", 3000);
      return;
    }

    // Compute total upload size for helpful UX text
    let totalSize = 0;
    for (const f of files) totalSize += f.size;
    const sizeMB = (totalSize / (1024 * 1024)).toFixed(2);
    
    const fileCount = files.length;
    const fileText = fileCount === 1 ? "1 file" : `${fileCount} files`;
    
    showProcessingOverlay(`Processing ${fileText} (${sizeMB} MB)...`);
    
    if (details) {
      details.textContent = `Uploading ${fileText}. You can view your chat history while waiting. This may take a minute for large files.`;
    }
    
    status.textContent = `Uploading ${fileText}...`;

    const form = new FormData();
    for (const f of files) form.append("files", f);

    try {
      console.log("[Upload] starting fetch /files/upload");
      const res = await fetch(`${API}/files/upload`, {
        method: "POST",
        headers: { ...authHeaders() },
        body: form,
      });

      // Read response text for logging / error messages
      const respText = await res.text().catch(()=> "");

      if (!res.ok) {
        console.error("[Upload] server returned error:", res.status, respText);
        status.textContent = "Upload failed — server error.";
        if (details) {
          details.textContent = "There was an error processing your files. Please try again.";
        }
        setTimeout(() => {
          hideProcessingOverlay();
          status.textContent = "";
        }, 2500);
        return;
      }

      console.log("[Upload] success, response:", respText);
      status.textContent = "Upload successful!";
      
      if (details) {
        details.textContent = "Files uploaded successfully. Rebuilding search index...";
      }

      await loadDocuments();

      // Clear status and overlay shortly after success
      setTimeout(() => {
        status.textContent = "";
        hideProcessingOverlay();
        fileInput.value = "";
      }, 800);

    } catch (err) {
      console.error("[Upload] network error", err);
      status.textContent = "Network error. Please try again.";
      if (details) {
        details.textContent = "Network connection error. Please check your connection and try again.";
      }
      setTimeout(() => {
        hideProcessingOverlay();
        status.textContent = "";
      }, 2000);
    }
  });

  // ------------------------
  // Load user's documents (files list)
  // ------------------------
  async function loadDocuments() {
    const container = qs("documentsList");
    if (!container) return;

    if (!token) {
      console.log("[Docs] no token, not loading docs");
      return;
    }

    try {
      console.log("[Docs] fetching /files/list");
      const res = await fetch(`${API}/files/list`, {
        headers: { ...authHeaders() }
      });

      if (!res.ok) {
        console.warn("[Docs] server returned", res.status);
        return;
      }

      const docs = await res.json();

      const tmp = document.createDocumentFragment();
      docs.forEach(d => {
        const row = document.createElement("div");
        row.className = "doc-row";
        // Use title attribute for full filename tooltip
        row.innerHTML = `
          <div class="name" title="${d.filename}">${d.filename}</div>
          <button class="doc-delete">Delete</button>
        `;

        // Delete handler: optimistic UI remove then call backend
        row.querySelector(".doc-delete").onclick = async () => {
          row.remove();
        
          try {
            const r = await fetch(`${API}/files/${d.id}`, {
              method: "DELETE",
              headers: { ...authHeaders() }
            });
          
            if (!r.ok) {
              console.warn("[Docs] delete failed", await r.text().catch(()=>""));
              await loadDocuments(); // reload on failure
            }
          } catch (err) {
            console.error("[Docs] delete error", err);
            await loadDocuments(); // reload on failure
          }
        };
  
        tmp.appendChild(row);
      });

      container.innerHTML = "";
      container.appendChild(tmp);

      console.log("[Docs] updated UI with", docs.length, "documents");
    } catch (err) {
      console.warn("[Docs] loadDocuments error", err);
    }
  }

  // Ensure docs UI matches current auth state on initial load
  updateDocsSection();
});

// ------------------------
// Global click handler for copy buttons inside rendered code blocks
// - Uses event delegation so copy buttons created dynamically work
// ------------------------
document.addEventListener("click", e => {
  if (!e.target.classList.contains("copy-btn")) return;

  // The code block is the next sibling in the markup generated in renderMessageWithCode()
  const code = e.target.nextElementSibling.innerText;
  navigator.clipboard.writeText(code).catch(() => {});

  e.target.textContent = "Copied ✓";
  setTimeout(() => (e.target.textContent = "Copy"), 1500);
});
