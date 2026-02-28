from playwright.sync_api import sync_playwright
import re


class CSSValidationService:
    """
    Robust CSS Validation Service.
    
    Strategy:
    1. Extract expected specs from Zeplin layers (if available).
    2. Always perform a comprehensive live-page audit that checks:
       - All visible text elements for font/color/size consistency
       - Key structural elements for layout dimensions
       - Common CSS best-practice violations
    3. Cross-reference Zeplin specs against live computed styles.
    """

    # Common selectors to always validate on any page
    STRUCTURAL_SELECTORS = [
        {"selector": "h1", "name": "H1 Heading", "props": ["font-size", "font-weight", "color", "font-family"]},
        {"selector": "h2", "name": "H2 Heading", "props": ["font-size", "font-weight", "color", "font-family"]},
        {"selector": "h3", "name": "H3 Heading", "props": ["font-size", "font-weight", "color", "font-family"]},
        {"selector": "p", "name": "Paragraph", "props": ["font-size", "line-height", "color", "font-family"]},
        {"selector": "a", "name": "Anchor Link", "props": ["font-size", "color", "text-decoration"]},
        {"selector": "button, .btn, [type='submit']", "name": "Button", "props": ["font-size", "color", "background-color", "border-radius", "padding"]},
        {"selector": "img", "name": "Image", "props": ["width", "height"]},
        {"selector": "nav, header", "name": "Navigation/Header", "props": ["height", "background-color"]},
        {"selector": "footer", "name": "Footer", "props": ["background-color", "color", "padding"]},
        {"selector": "input, textarea, select", "name": "Form Input", "props": ["font-size", "border", "border-radius", "padding"]},
    ]

    @staticmethod
    def extract_specs_from_zeplin(zeplin_data):
        """
        Extracts expected CSS properties from Zeplin JSON layers data.
        Returns a list of specs with selectors and expected values.
        """
        specs = []
        layers = zeplin_data.get('layers', [])
        
        for layer in layers:
            if layer.get('type') == 'text' and 'content' in layer:
                text_content = layer['content'].strip()
                if not text_content:
                    continue
                    
                style = layer.get('style', {})
                font = style.get('font', {})
                color = style.get('color', {})
                
                expected_css = {}
                if 'size' in font:
                    expected_css['font-size'] = f"{font['size']}px"
                if 'family' in font:
                    expected_css['font-family'] = font['family']
                if 'line_height' in font:
                    expected_css['line-height'] = f"{font['line_height']}px"
                if 'r' in color:
                    r, g, b = color.get('r', 0), color.get('g', 0), color.get('b', 0)
                    expected_css['color'] = f"rgb({r}, {g}, {b})"
                    
                rect = layer.get('rect', {})
                if 'width' in rect:
                    expected_css['width'] = f"{rect['width']}px"
                if 'height' in rect:
                    expected_css['height'] = f"{rect['height']}px"
                    
                if expected_css:
                    safe_text = text_content[:30].replace('"', '\\"')
                    specs.append({
                        "selector": f'text="{safe_text}"', 
                        "name": f"Zeplin Layer: {text_content[:40]}",
                        "expected": expected_css,
                        "source": "zeplin"
                    })
        
        return specs

    @staticmethod
    def _extract_live_element_styles(page):
        """
        Crawls the live page and extracts computed CSS for all major visible elements.
        Returns a structured list of element data.
        """
        return page.evaluate("""() => {
            const results = [];
            const selectors = [
                { sel: 'h1', name: 'H1 Heading' },
                { sel: 'h2', name: 'H2 Heading' },
                { sel: 'h3', name: 'H3 Heading' },
                { sel: 'h4', name: 'H4 Heading' },
                { sel: 'p', name: 'Paragraph' },
                { sel: 'a', name: 'Anchor Link' },
                { sel: 'button, .btn, [type="submit"]', name: 'Button' },
                { sel: 'img', name: 'Image' },
                { sel: 'nav, header, [role="navigation"]', name: 'Navigation' },
                { sel: 'footer', name: 'Footer' },
                { sel: 'input, textarea, select', name: 'Form Input' },
                { sel: 'li', name: 'List Item' },
                { sel: 'span', name: 'Span' },
                { sel: 'div', name: 'Div Container' },
            ];
            
            const props = [
                'font-size', 'font-family', 'font-weight', 'color',
                'background-color', 'line-height', 'padding', 'margin',
                'border', 'border-radius', 'text-decoration', 'text-align',
                'width', 'height', 'display', 'position'
            ];
            
            for (const { sel, name } of selectors) {
                const els = document.querySelectorAll(sel);
                // Only check up to 5 instances of each type to keep report manageable
                const limit = Math.min(els.length, 5);
                for (let i = 0; i < limit; i++) {
                    const el = els[i];
                    const rect = el.getBoundingClientRect();
                    
                    // Skip invisible/off-screen elements
                    if (rect.width === 0 && rect.height === 0) continue;
                    if (rect.top > 5000) continue;
                    
                    const cs = window.getComputedStyle(el);
                    const styles = {};
                    for (const p of props) {
                        styles[p] = cs.getPropertyValue(p);
                    }
                    
                    const text = (el.textContent || '').trim().substring(0, 50);
                    const tag = el.tagName.toLowerCase();
                    const classes = el.className && typeof el.className === 'string' 
                        ? el.className.split(' ').slice(0, 3).join('.') 
                        : '';
                    
                    results.push({
                        selector: `${tag}${classes ? '.' + classes : ''}`,
                        name: `${name}${i > 0 ? ' #' + (i+1) : ''}`,
                        text: text,
                        tag: tag,
                        styles: styles,
                        position: {
                            x: Math.round(rect.x),
                            y: Math.round(rect.y),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        }
                    });
                }
            }
            return results;
        }""")

    @staticmethod
    def _check_zeplin_specs(page, zeplin_specs):
        """
        Validates Zeplin-extracted specs against the live page.
        """
        mismatches = []
        for spec in zeplin_specs:
            selector = spec['selector']
            name = spec['name']
            expected = spec['expected']
            
            try:
                locator = page.locator(selector).first
                locator.wait_for(state="attached", timeout=2000)
                
                for prop, exp_val in expected.items():
                    actual_val = locator.evaluate(
                        f"(el) => window.getComputedStyle(el).getPropertyValue('{prop}')"
                    )
                    if str(actual_val).strip() != str(exp_val).strip():
                        mismatches.append({
                            "element": name,
                            "property": prop,
                            "expected": exp_val,
                            "actual": actual_val,
                            "source": "zeplin",
                            "status": "FAIL"
                        })
            except Exception:
                mismatches.append({
                    "element": name,
                    "property": "element_found",
                    "expected": "visible",
                    "actual": "not_found",
                    "source": "zeplin",
                    "status": "FAIL"
                })
        return mismatches

    @staticmethod
    def _audit_live_page(page, zeplin_data):
        """
        Performs a comprehensive CSS audit of the live page.
        Each defect includes: element, property, expected, actual, selector, severity,
        description (human-readable), and css_fix (copy-paste CSS snippet).
        """
        mismatches = []
        live_elements = CSSValidationService._extract_live_element_styles(page)
        
        screen = zeplin_data.get('screen', {})
        screen_width = screen.get('width')

        # --- Check 1: Font consistency across same element types ---
        font_map = {}
        for el in live_elements:
            tag = el['tag']
            font = el['styles'].get('font-family', '')
            size = el['styles'].get('font-size', '')
            weight = el['styles'].get('font-weight', '')
            color = el['styles'].get('color', '')
            line_h = el['styles'].get('line-height', '')
            if tag in ('h1', 'h2', 'h3', 'h4', 'p', 'a', 'button', 'li', 'span'):
                key = tag
                if key not in font_map:
                    font_map[key] = {
                        'font': font, 'size': size, 'weight': weight,
                        'color': color, 'line_height': line_h,
                        'name': el['name'], 'selector': el['selector']
                    }
                else:
                    ref = font_map[key]
                    if font != ref['font']:
                        mismatches.append({
                            "element": f"{el['name']} — \"{el.get('text', '')[:25]}\"",
                            "property": "font-family",
                            "expected": ref['font'],
                            "actual": font,
                            "selector": el['selector'],
                            "location": f"({el['position']['x']}, {el['position']['y']}) — {el['position']['width']}x{el['position']['height']}px",
                            "severity": "medium",
                            "description": f"This {tag.upper()} uses a different font-family than the first {tag.upper()} on the page. All {tag.upper()} elements should use the same font for visual consistency.",
                            "css_fix": f"{el['selector']} {{\n  font-family: {ref['font']};\n}}",
                            "source": "audit",
                            "status": "WARN"
                        })
                    if size != ref['size']:
                        mismatches.append({
                            "element": f"{el['name']} — \"{el.get('text', '')[:25]}\"",
                            "property": "font-size",
                            "expected": ref['size'],
                            "actual": size,
                            "selector": el['selector'],
                            "location": f"({el['position']['x']}, {el['position']['y']}) — {el['position']['width']}x{el['position']['height']}px",
                            "severity": "high",
                            "description": f"Font size mismatch: This {tag.upper()} is {size} but the primary {tag.upper()} is {ref['size']}. This breaks the visual hierarchy and likely does not match the Zeplin design.",
                            "css_fix": f"{el['selector']} {{\n  font-size: {ref['size']};\n}}",
                            "source": "audit",
                            "status": "FAIL"
                        })
                    if color != ref['color']:
                        mismatches.append({
                            "element": f"{el['name']} — \"{el.get('text', '')[:25]}\"",
                            "property": "color",
                            "expected": ref['color'],
                            "actual": color,
                            "selector": el['selector'],
                            "location": f"({el['position']['x']}, {el['position']['y']}) — {el['position']['width']}x{el['position']['height']}px",
                            "severity": "medium",
                            "description": f"Text color inconsistency: This {tag.upper()} has color {color} but the primary {tag.upper()} uses {ref['color']}.",
                            "css_fix": f"{el['selector']} {{\n  color: {ref['color']};\n}}",
                            "source": "audit",
                            "status": "WARN"
                        })

        # --- Check 2: Viewport width compliance ---
        if screen_width:
            for el in live_elements:
                el_width = el['position'].get('width', 0)
                if el['tag'] in ('div', 'nav', 'header', 'footer', 'section', 'main'):
                    if el_width > screen_width + 20:
                        mismatches.append({
                            "element": f"{el['name']} ({el['selector']})",
                            "property": "width (overflow)",
                            "expected": f"<= {screen_width}px",
                            "actual": f"{el_width}px",
                            "selector": el['selector'],
                            "location": f"({el['position']['x']}, {el['position']['y']})",
                            "severity": "critical",
                            "description": f"This element is {el_width - screen_width}px wider than the Zeplin design width ({screen_width}px). This causes horizontal scrollbar and layout overflow.",
                            "css_fix": f"{el['selector']} {{\n  max-width: {screen_width}px;\n  overflow-x: hidden;\n}}",
                            "source": "audit",
                            "status": "FAIL"
                        })

        # --- Check 3: Images without proper dimensions ---
        for el in live_elements:
            if el['tag'] == 'img':
                w = el['position'].get('width', 0)
                h = el['position'].get('height', 0)
                if w == 0 or h == 0:
                    mismatches.append({
                        "element": f"{el['name']} ({el['selector']})",
                        "property": "dimensions",
                        "expected": "visible width & height > 0",
                        "actual": f"{w}x{h}px (broken/hidden)",
                        "selector": el['selector'],
                        "location": f"({el['position']['x']}, {el['position']['y']})",
                        "severity": "high",
                        "description": "This image has zero width or height — it is either broken (missing src), hidden by CSS, or has not loaded. Check the image src attribute and any CSS rules hiding it.",
                        "css_fix": f"/* Check the img src attribute in HTML */\n{el['selector']} {{\n  display: block;\n  min-width: 100px;\n  min-height: 100px;\n}}",
                        "source": "audit",
                        "status": "FAIL"
                    })

        # --- Check 4: Text readability (contrast check) ---
        for el in live_elements:
            if el['tag'] in ('p', 'span', 'a', 'li', 'h1', 'h2', 'h3', 'h4', 'button'):
                color = el['styles'].get('color', '')
                bg = el['styles'].get('background-color', '')
                if color and bg and color == bg:
                    mismatches.append({
                        "element": f"{el['name']} — \"{el.get('text', '')[:25]}\"",
                        "property": "color vs background-color",
                        "expected": "text and background must differ",
                        "actual": f"both are {color}",
                        "selector": el['selector'],
                        "location": f"({el['position']['x']}, {el['position']['y']}) — {el['position']['width']}x{el['position']['height']}px",
                        "severity": "critical",
                        "description": f"INVISIBLE TEXT: The text color and background color are both {color}. Users cannot read this element. This is an accessibility violation (WCAG 2.1).",
                        "css_fix": f"{el['selector']} {{\n  color: #333333; /* or appropriate contrasting color */\n  /* OR */\n  background-color: transparent;\n}}",
                        "source": "audit",
                        "status": "FAIL"
                    })
        
        # --- Check 5: Build element inventory ---
        element_inventory = []
        for el in live_elements:
            entry = {
                "element": f"{el['name']}",
                "selector": el['selector'],
                "text": el.get('text', '')[:40],
                "position": f"({el['position']['x']}, {el['position']['y']})",
                "size": f"{el['position']['width']}x{el['position']['height']}px",
                "font": el['styles'].get('font-family', 'N/A')[:40],
                "font_size": el['styles'].get('font-size', 'N/A'),
                "font_weight": el['styles'].get('font-weight', 'N/A'),
                "color": el['styles'].get('color', 'N/A'),
                "bg_color": el['styles'].get('background-color', 'N/A'),
                "line_height": el['styles'].get('line-height', 'N/A'),
                "padding": el['styles'].get('padding', 'N/A'),
                "margin": el['styles'].get('margin', 'N/A'),
            }
            element_inventory.append(entry)

        return mismatches, element_inventory

    @staticmethod
    def validate_css(url, zeplin_data):
        """
        Full CSS validation pipeline:
        1. Check Zeplin layer specs (if any)
        2. Perform comprehensive live-page CSS audit
        Returns: (mismatches_list, element_inventory_list)
        """
        zeplin_specs = CSSValidationService.extract_specs_from_zeplin(zeplin_data)
        mismatches = []
        element_inventory = []
        
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page(viewport={'width': 1440, 'height': 900})
            
            try:
                page.goto(url, wait_until='networkidle', timeout=60000)
                page.wait_for_timeout(2000)
                
                # Step 1: Zeplin layer validation
                if zeplin_specs:
                    zeplin_mismatches = CSSValidationService._check_zeplin_specs(page, zeplin_specs)
                    mismatches.extend(zeplin_mismatches)
                
                # Step 2: Live page CSS audit
                audit_mismatches, element_inventory = CSSValidationService._audit_live_page(page, zeplin_data)
                mismatches.extend(audit_mismatches)
                
            finally:
                browser.close()
                
        return mismatches, element_inventory
