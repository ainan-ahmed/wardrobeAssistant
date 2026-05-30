export interface WardrobeItem {
  id: string;
  original_image_path: string;
  processed_image_path: string;
  category: string;
  subcategory?: string;
  colors: string[];
  style_tags: string[];
  ai_description?: string;
  brand?: string;
  times_worn: number;
  is_active: boolean;
}
