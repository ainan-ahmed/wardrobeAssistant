import React, { useState, useEffect } from 'react';
import {
  Drawer, Button, Group, TextInput, Textarea, Text, Image,
  Stack, Box, Badge, TagsInput, Switch, Loader,
} from '@mantine/core';
import { IconEdit, IconCheck, IconX, IconTrash } from '@tabler/icons-react';
import axios from 'axios';
import { WardrobeItem } from '../types';

interface ClosetItemDrawerProps {
  item: WardrobeItem | null;
  opened: boolean;
  onClose: () => void;
  onUpdate: () => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
}

export const ClosetItemDrawer: React.FC<ClosetItemDrawerProps> = ({
  item, opened, onClose, onUpdate, onDelete,
}) => {
  const [editMode, setEditMode] = useState(false);
  const [loading, setLoading] = useState(false);

  // Editable fields state
  const [brand, setBrand] = useState('');
  const [category, setCategory] = useState('');
  const [subcategory, setSubcategory] = useState('');
  const [aiDescription, setAiDescription] = useState('');
  const [colors, setColors] = useState<string[]>([]);
  const [styleTags, setStyleTags] = useState<string[]>([]);
  const [isActive, setIsActive] = useState(true);

  // Initialize state when item changes
  useEffect(() => {
    if (item) {
      setBrand(item.brand || '');
      setCategory(item.category || '');
      setSubcategory(item.subcategory || '');
      setAiDescription(item.ai_description || '');
      setColors(item.colors || []);
      setStyleTags(item.style_tags || []);
      setIsActive(item.is_active ?? true);
      setEditMode(false);
    }
  }, [item]);

  if (!item) return null;

  const handleSave = async () => {
    setLoading(true);
    try {
      await axios.patch(`/api/items/${item.id}`, {
        brand: brand.trim(),
        category: category.toLowerCase().trim(),
        subcategory: subcategory.trim(),
        ai_description: aiDescription.trim(),
        colors,
        style_tags: styleTags,
        is_active: isActive,
      });
      onUpdate();
      setEditMode(false);
    } catch (err) {
      console.error('Failed to update item:', err);
      alert('Failed to save changes. Make sure backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleCustomDelete = (e: React.MouseEvent) => {
    onDelete(e, item.id);
    onClose();
  };

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={
        <Text fw={700} size="lg" className="editorial-header">
          {editMode ? 'Edit Garment Details' : 'Garment Profile'}
        </Text>
      }
      position="right"
      size="md"
    >
      <Stack gap="lg" className="drawer-scroll-area">
        
        {/* Large Centered Image Cutout */}
        <Box
          className="drawer-image-box"
        >
          <Image
            src={`/${item.processed_image_path || item.original_image_path}`}
            alt={brand || 'Garment Profile'}
            className="isolated-cutout drawer-image-file"
          />
        </Box>

        {editMode ? (
          /* ── EDIT MODE CONTROLS ── */
          <Stack gap="md">
            <TextInput
              label="Brand"
              value={brand}
              onChange={(e) => setBrand(e.currentTarget.value)}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <TextInput
              label="Category"
              value={category}
              onChange={(e) => setCategory(e.currentTarget.value)}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <TextInput
              label="Subcategory"
              value={subcategory}
              onChange={(e) => setSubcategory(e.currentTarget.value)}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <Textarea
              label="AI Description"
              value={aiDescription}
              onChange={(e) => setAiDescription(e.currentTarget.value)}
              variant="filled"
              autosize
              minRows={3}
              classNames={{ input: 'elegant-text-input' }}
            />
            <TagsInput
              label="Colors"
              placeholder="Type color and press enter"
              value={colors}
              onChange={setColors}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <TagsInput
              label="Style Tags"
              placeholder="Type tag and press enter"
              value={styleTags}
              onChange={setStyleTags}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <Switch
              label="Active In Closet"
              checked={isActive}
              onChange={(e) => setIsActive(e.currentTarget.checked)}
              color="amber"
            />

            <Group gap="xs" mt="lg">
              <Button
                flex={1}
                color="amber"
                onClick={handleSave}
                disabled={loading}
                leftSection={loading ? <Loader size="xs" color="white" /> : <IconCheck size={16} />}
              >
                Save Profile
              </Button>
              <Button
                variant="outline"
                color="gray"
                onClick={() => setEditMode(false)}
                leftSection={<IconX size={16} />}
              >
                Cancel
              </Button>
            </Group>
          </Stack>
        ) : (
          /* ── VIEW MODE CONTROLS ── */
          <Stack gap="md">
            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" className="meta-label-upper">Brand</Text>
                <Text fw={700} size="md" c="amber" tt="uppercase">
                  {item.brand || 'Minimalist'}
                </Text>
              </div>
              <div>
                <Text size="xs" c="dimmed" className="meta-label-upper">Times Worn</Text>
                <Text fw={700} size="md" ta="right">
                  {item.times_worn}
                </Text>
              </div>
            </Group>

            <Group justify="space-between">
              <div>
                <Text size="xs" c="dimmed" className="meta-label-upper">Category</Text>
                <Text size="sm" tt="capitalize">{item.category}</Text>
              </div>
              <div>
                <Text size="xs" c="dimmed" className="meta-label-upper">Subcategory</Text>
                <Text size="sm" tt="capitalize">{item.subcategory || 'Unspecified'}</Text>
              </div>
            </Group>

            <div>
              <Text size="xs" c="dimmed" mb={4} className="meta-label-upper">Stylist's Breakdown</Text>
              <Text size="sm">
                {item.ai_description || 'No detailed analysis generated.'}
              </Text>
            </div>

            <div>
              <Text size="xs" c="dimmed" mb={6} className="meta-label-upper">Palette Swatches</Text>
              <Group gap="xs">
                {item.colors.length === 0 ? (
                  <Text size="xs" c="dimmed">No colors identified.</Text>
                ) : (
                  item.colors.map((color, idx) => (
                    <Group key={idx} gap={6} align="center">
                      <div
                        className="color-swatch-circle"
                        style={{
                          backgroundColor: color,
                        }}
                      />
                      <Text size="xs">{color}</Text>
                    </Group>
                  ))
                )}
              </Group>
            </div>

            <div>
              <Text size="xs" c="dimmed" mb={6} className="meta-label-upper">Style DNA Tags</Text>
              <Group gap="xs">
                {item.style_tags.length === 0 ? (
                  <Text size="xs" c="dimmed">No style tags generated.</Text>
                ) : (
                  item.style_tags.map((tag, idx) => (
                    <Badge key={idx} variant="light" color="amber" radius="sm">
                      {tag}
                    </Badge>
                  ))
                )}
              </Group>
            </div>

            <Group gap="xs" mt="lg">
              <Button
                flex={1}
                color="amber"
                variant="light"
                onClick={() => setEditMode(true)}
                leftSection={<IconEdit size={16} />}
              >
                Edit Details
              </Button>
              <Button
                variant="outline"
                color="red"
                onClick={handleCustomDelete}
                leftSection={<IconTrash size={16} />}
              >
                Remove Item
              </Button>
            </Group>
          </Stack>
        )}
      </Stack>
    </Drawer>
  );
};
