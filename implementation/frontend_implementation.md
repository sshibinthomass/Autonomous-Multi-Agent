# Frontend Architecture & Flow Implementation (`frontend`)

This document outlines the technical details and flow charts for the React + TypeScript frontend client located in the `/frontend` directory.

---

## 🛠️ Tech Stack Specifications

- **Core**: [React 19](https://react.dev/) & [TypeScript](https://www.typescriptlang.org/) for robust static type checking.
- **Build System**: [Vite](https://vite.dev/) for extremely fast Hot Module Replacement (HMR) and compilation.
- **Styling**: Pure **Vanilla CSS** with unified custom HSL color palettes and smooth typography. No bulky grid libraries or tailwind templates are used, ensuring a clean and lightweight package size.

---

## 📂 Codebase Structures

```
frontend/
├── package.json         # NPM script setups and dependencies
├── vite.config.ts       # Vite bundler parameters
├── index.html           # Main template target
└── src/
    ├── main.tsx         # Entry point executing React tree render
    ├── App.tsx          # Master Chat Dashboard containing reactive states
    ├── App.css          # Customized HSL layout themes and keyframe anims
    └── index.css        # Simple CSS reset clearing default templates
```

---

## 💾 State Machine Schema (`App.tsx`)

To keep the application highly responsive, `App.tsx` manages a centralized series of reactive states:

| State Variable | Data Type | Purpose |
| :--- | :--- | :--- |
| `messages` | `Message[]` | The array of conversational steps rendering in the chat screen (System, Human, AI bubbles). |
| `providers` | `Record<string, ProviderInfo>` | List of LLM options and environmental key availability flags populated by `/api/settings` on load. |
| `selectedProvider` | `string` | The active LLM engine category selected (e.g. `openai`, `gemini`). |
| `selectedModel` | `string` | The specific model string selected within the provider subgroup (e.g. `gpt-4o-mini`). |
| `isLoading` | `boolean` | Flag to trigger visual loader (typing dot animation) and disable input forms. |
| `errorMsg` | `string \| null` | Stores API exception alerts for dynamic UI banners. |

---

## 🔄 User Interaction Flows

### 1. Initialization Flow (Component Mount)
```mermaid
graph TD
    A([App Mounts]) --> B[Fetch GET http://127.0.0.1:8080/api/settings]
    B --> C{Success?}
    C -- No --> D[Render network connection error banner]
    C -- Yes --> E[Save providers state config]
    E --> F[Select first provider that has preconfigured API key in .env]
    F --> G[Load default model list for selected provider]
```

### 2. Message Transmission Flow
When the user types a prompt and submits the chat input:
1. **Local Update**:
   - Create a message dictionary: `{ role: 'user', content: inputValue }`.
   - Append to `messages` state list (instantly renders human speech bubble on the right).
   - Clear input text field.
   - Set `isLoading = true` (disables input bar and triggers typing dots loading bubble).
2. **API Dispatch**:
   - Send `POST` request to `http://127.0.0.1:8080/api/chat` with body:
     ```json
     {
       "messages": [...allMessages, userMessage],
       "provider": "selectedProvider",
       "model": "selectedModel"
     }
     ```
3. **API Resolution**:
   - On success: append the returned `{ role: 'assistant', content: '...' }` to the message state list.
   - On error: display red alert banner with error details.
   - Turn `isLoading = false` (input elements re-enable, dots fade out).
4. **Layout Sync**:
   - Use `useRef()` element bindings to smoothly scroll the chat log to the bottom, ensuring the new response is visible.

---

## 🎨 Styling Specifications (`App.css`)

The application adopts a **Modern Tech Dark Aesthetic** using customized CSS variables:

### 1. CSS Custom Properties
```css
:root {
  --bg-primary: #121316;     /* Full dark base background */
  --bg-secondary: #1a1c22;   /* Card, header, sidebar panel color */
  --border-color: #2a2e37;   /* Slim borders separator */
  --text-main: #f3f4f6;
  --primary: #3b82f6;        /* Bright neon blue for human speech bubble and buttons */
  --bot-bg: #292d38;         /* Deep slate for AI messages */
}
```

### 2. Micro-Animations (Typing Dots Bounce)
To provide instant interactive feedback during AI invocation, the loading bubble features a clean, CSS-based typing indicator. Individual span dots bounce with staggered keyframe delays:
```css
.typing-dots span {
  width: 6px;
  height: 6px;
  background-color: var(--text-muted);
  border-radius: 50%;
  animation: bounce 1.3s infinite ease-in-out both;
}
.typing-dots span:nth-child(1) { animation-delay: -0.32s; }
.typing-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1.0); }
}
```
