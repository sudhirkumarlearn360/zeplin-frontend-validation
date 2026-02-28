from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch

class ComparisonService:
    @staticmethod
    def compare_images(design_path, live_path, diff_path, threshold=0.1):
        """
        Compares two images using pixelmatch.
        Returns a tuple: (mismatch_pixel_count, list_of_bounding_boxes)
        """
        img1 = Image.open(design_path).convert("RGBA")
        img2 = Image.open(live_path).convert("RGBA")
        
        # Ensure sizes match by creating a blank canvas of the max dimensions
        width = max(img1.width, img2.width)
        height = max(img1.height, img2.height)
        
        img1_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        img1_canvas.paste(img1, (0, 0))
        
        img2_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        img2_canvas.paste(img2, (0, 0))
        
        diff = Image.new("RGBA", (width, height))
        
        # Compare images
        mismatch = pixelmatch(img1_canvas, img2_canvas, diff, threshold=threshold, includeAA=True)
        
        # Save diff image
        diff.save(diff_path)
        
        # Calculate bounding boxes of mismatches
        # Pixelmatch creates a diff image where mismatches are typically bright red (255, 0, 0, 255)
        # Or at least not transparent/black if they are differents.
        diff_data = diff.getdata()
        
        boxes = ComparisonService._find_mismatch_regions(diff_data, width, height)
        
        return mismatch, boxes

    @staticmethod
    def _find_mismatch_regions(diff_data, width, height, region_size=50):
        """
        Groups mismatched pixels into rough bounding boxes to indicate WHERE on the screen failures occurred.
        We grid the screen into `region_size` blocks and flag blocks that contain mismatches.
        Returns a list of dicts: {'x': int, 'y': int, 'width': int, 'height': int}
        """
        mismatch_blocks = set()
        
        for y in range(height):
            for x in range(width):
                # Diff pixel format is RGBA (r, g, b, a)
                pixel = diff_data[y * width + x]
                # Pixelmatch colors diff pixels red (255, 0, 0)
                if pixel[0] > 200 and pixel[1] < 50 and pixel[2] < 50 and pixel[3] > 0:
                    # Found a mismatch, map it to a grid block
                    block_x = (x // region_size) * region_size
                    block_y = (y // region_size) * region_size
                    mismatch_blocks.add((block_x, block_y))
                    
        # Convert blocks to bounding box dicts
        regions = []
        for bx, by in sorted(list(mismatch_blocks)):
            regions.append({
                'x': bx,
                'y': by,
                'width': min(region_size, width - bx),
                'height': min(region_size, height - by)
            })
            
        return regions
