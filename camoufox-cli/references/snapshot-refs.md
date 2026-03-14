# Snapshot and Refs

Compact element references for AI agents to interact with page elements efficiently.

**Related**: [commands.md](commands.md) for full command reference, [SKILL.md](../SKILL.md) for quick start.

## How Refs Work

Traditional approach:
```
Full DOM/HTML -> AI parses -> CSS selector -> Action (~3000-5000 tokens)
```

camoufox-cli approach:
```
Compact aria snapshot -> @refs assigned -> Direct interaction (~200-400 tokens)
```

Refs are sequential numbers (`@e1`, `@e2`, ...) assigned to elements during each snapshot based on DOM traversal order. The same element may get different refs across snapshots if the page content changes.

## The Snapshot Command

```bash
# Basic snapshot (shows full page structure)
camoufox-cli snapshot

# Interactive snapshot (-i flag) - RECOMMENDED
camoufox-cli snapshot -i

# Scoped to a specific container
camoufox-cli snapshot -s "#main-content"
camoufox-cli snapshot -i -s "form.login"
```

### Snapshot Output Format

```
- heading "Example Domain" [ref=e1]
- navigation
  - link "Home" [ref=e2]
  - link "Products" [ref=e3]
  - link "About" [ref=e4]
- button "Sign In" [ref=e5]
- main
  - heading "Welcome" [ref=e6]
  - textbox "Email" [ref=e7]
  - textbox "Password" [ref=e8]
  - button "Log In" [ref=e9]
- contentinfo
  - link "Privacy Policy" [ref=e10]
```

With `-i` (interactive only), non-interactive elements are filtered out:

```
- link "Home" [ref=e1]
- link "Products" [ref=e2]
- link "About" [ref=e3]
- button "Sign In" [ref=e4]
- textbox "Email" [ref=e5]
- textbox "Password" [ref=e6]
- button "Log In" [ref=e7]
- link "Privacy Policy" [ref=e8]
```

## Using Refs

Once you have refs, interact directly:

```bash
camoufox-cli click @e4               # Click the "Sign In" button
camoufox-cli fill @e5 "user@example.com"  # Fill email input
camoufox-cli fill @e6 "password123"  # Fill password
camoufox-cli click @e7               # Submit the form
```

## Ref Lifecycle

**IMPORTANT**: Refs are invalidated when the page changes!

### What Invalidates Refs

- **Navigation**: clicking links, form submissions, redirects
- **Dynamic content**: dropdowns opening, modals appearing, AJAX updates
- **Scrolling**: if it triggers lazy loading of new content
- **JavaScript**: any DOM mutation that changes element order

### What Happens with Stale Refs

- The ref may point to a **different element** (wrong click target)
- The ref may **not exist** (error)
- The action may **silently succeed on the wrong element**

This is the most common source of automation errors. When in doubt, re-snapshot.

## Best Practices

### 1. Always Snapshot Before Interacting

```bash
# CORRECT
camoufox-cli open https://example.com
camoufox-cli snapshot -i
camoufox-cli click @e1

# WRONG
camoufox-cli open https://example.com
camoufox-cli click @e1            # Ref doesn't exist yet!
```

### 2. Re-Snapshot After Navigation

```bash
camoufox-cli click @e5            # Navigates to new page
camoufox-cli snapshot -i          # Get new refs
camoufox-cli click @e1            # Use new refs
```

### 3. Re-Snapshot After Dynamic Changes

```bash
camoufox-cli click @e1            # Opens dropdown
camoufox-cli snapshot -i          # See dropdown items
camoufox-cli click @e7            # Select item
```

### 4. Scope Snapshots on Complex Pages

```bash
camoufox-cli snapshot -i -s "#login-form"
camoufox-cli snapshot -i -s ".product-list"
```

### 5. Wait Before Snapshot on Slow Pages

```bash
camoufox-cli open https://slow-site.com
camoufox-cli wait 3000
camoufox-cli snapshot -i
```

## Troubleshooting

### "Ref @eN not found"
Re-snapshot: `camoufox-cli snapshot -i`

### Element Not Visible in Snapshot
```bash
camoufox-cli scroll down 1000 && camoufox-cli snapshot -i
```

### Too Many Elements
```bash
camoufox-cli snapshot -i -s "#main"
```

### Duplicate Elements (Same Role + Name)
Each gets a unique ref with `[nth=N]` for disambiguation:
```
- button "Submit" [ref=e3]
- button "Submit" [ref=e7] [nth=1]
```
