import re

class ZeplinToHtmlService:
    @staticmethod
    def generate_html_css(screen_data, layers):
        """
        Takes Zeplin screen and layer data and converts it into a standalone HTML/CSS document.
        Uses absolute positioning to precisely match the Zeplin canvas.
        """
        if not screen_data or not layers:
            return "<html><body><h1>No Zeplin Data Found</h1></body></html>"
            
        screen_width = screen_data.get('image', {}).get('width', 1440)
        screen_height = screen_data.get('image', {}).get('height', 1000)
        bg_color = screen_data.get('background_color', {}).get('r', 255)
        bg_color_g = screen_data.get('background_color', {}).get('g', 255)
        bg_color_b = screen_data.get('background_color', {}).get('b', 255)
        bg_color_a = screen_data.get('background_color', {}).get('a', 1)
        
        css_rules = [
            "* { box-sizing: border-box; margin: 0; padding: 0; }",
            "body {",
            f"  background-color: rgba({bg_color}, {bg_color_g}, {bg_color_b}, {bg_color_a});",
            "  font-family: sans-serif;",
            "}",
            "#zeplin-canvas {",
            f"  width: {screen_width}px;",
            f"  height: {screen_height}px;",
            "  position: relative;",
            "  margin: 0 auto;",
            "  overflow: hidden;",
            "  background-color: #ffffff;",
            "  box-shadow: 0 0 20px rgba(0,0,0,0.1);",
            "}"
        ]
        
        html_elements = []
        
        # Reverse layers so background elements are rendered first
        for idx, layer in enumerate(reversed(layers)):
            layer_id = f"layer-{idx}"
            tag = "div"
            content = ""
            
            rect = layer.get('rect', {})
            x = rect.get('x', 0)
            y = rect.get('y', 0)
            w = rect.get('width', 0)
            h = rect.get('height', 0)
            
            style_props = [
                "position: absolute;",
                f"left: {x}px;",
                f"top: {y}px;",
                f"width: {w}px;",
                f"height: {h}px;"
            ]
            
            if layer.get('type') == 'text':
                content = layer.get('content', '')
                content = content.replace('\n', '<br>')
                
                texts = layer.get('texts', [])
                if texts:
                    t_style = texts[0].get('style', {})
                    font_size = t_style.get('font_size', 14)
                    font_weight = t_style.get('font_weight', 400)
                    font_family = t_style.get('font_family', 'sans-serif')
                    color = t_style.get('color', {})
                    r, g, b, a = color.get('r', 0), color.get('g', 0), color.get('b', 0), color.get('a', 1)
                    
                    style_props.append(f"font-size: {font_size}px;")
                    style_props.append(f"font-weight: {font_weight};")
                    style_props.append(f"font-family: '{font_family}', sans-serif;")
                    style_props.append(f"color: rgba({r}, {g}, {b}, {a});")
                    style_props.append("line-height: 1.2;") # approximation
                    
            elif layer.get('fills'):
                fills = layer.get('fills', [])
                if fills:
                    color = fills[0].get('color', {})
                    r, g, b, a = color.get('r', 0), color.get('g', 0), color.get('b', 0), color.get('a', 1)
                    style_props.append(f"background-color: rgba({r}, {g}, {b}, {a});")
            
            if layer.get('borders'):
                borders = layer.get('borders', [])
                if borders:
                    b_color = borders[0].get('color', {})
                    r, g, b, a = b_color.get('r', 0), b_color.get('g', 0), b_color.get('b', 0), b_color.get('a', 1)
                    b_thick = borders[0].get('thickness', 1)
                    style_props.append(f"border: {b_thick}px solid rgba({r}, {g}, {b}, {a});")
                    
            if layer.get('border_radius'):
                br = layer.get('border_radius')
                style_props.append(f"border-radius: {br}px;")
                
            if layer.get('opacity') is not None and layer.get('opacity') < 1.0:
                style_props.append(f"opacity: {layer.get('opacity')};")
            
            css_rules.append(f"#{layer_id} {{ {' '.join(style_props)} }}")
            
            html_elements.append(f'    <{tag} id="{layer_id}" title="{layer.get("name", "")}">{content}</{tag}>')
            
        final_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Zeplin Generated Code: {screen_data.get('name', 'Screen')}</title>
    <style>
{chr(10).join(css_rules)}
    </style>
</head>
<body>
    <div id="zeplin-canvas">
{chr(10).join(html_elements)}
    </div>
</body>
</html>
"""
        return final_html
