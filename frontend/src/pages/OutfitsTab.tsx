import React, { useState, useEffect } from 'react';
import {
  Card, Text, Button, Select, SimpleGrid, Group, Stack, Image,
  Badge, ActionIcon, Loader, Box, Divider,
} from '@mantine/core';
import { IconSparkles, IconCheck, IconTrash, IconCalendarEvent } from '@tabler/icons-react';
import axios from 'axios';
import { WardrobeItem } from '../domains/wardrobe/types';

interface Outfit {
  id: string;
  name: string;
  item_ids: string[];
  occasion: string;
  ai_rationale: string;
  created_at: string;
}

interface OutfitsTabProps {
  wardrobeItems: WardrobeItem[];
}

export const OutfitsTab: React.FC<OutfitsTabProps> = ({ wardrobeItems }) => {
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [loading, setLoading] = useState(false);
  const [occasion, setOccasion] = useState<string | null>('casual');
  const [weather, setWeather] = useState<string | null>('mild');
  const [style, setStyle] = useState<string | null>('minimalist');

  const fetchOutfits = async () => {
    try {
      const res = await axios.get<Outfit[]>('/api/outfits/');
      setOutfits(res.data);
    } catch (err) {
      console.error('Failed to fetch outfits:', err);
    }
  };

  useEffect(() => {
    fetchOutfits();
  }, []);

  const generateOutfit = async () => {
    setLoading(true);
    try {
      await axios.post('/api/outfits/suggest', {
        occasion,
        weather,
        style,
      });
      fetchOutfits();
    } catch (err) {
      console.error('Failed to generate outfit:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLogWorn = async (id: string) => {
    try {
      await axios.post(`/api/outfits/${id}/worn`);
      alert('Logged worn successfully! Item counters updated.');
    } catch (err) {
      console.error('Failed to log worn:', err);
    }
  };

  const handleDeleteOutfit = async (id: string) => {
    if (!window.confirm('Delete this outfit recommendation?')) return;
    try {
      await axios.delete(`/api/outfits/${id}`);
      fetchOutfits();
    } catch (err) {
      console.error('Failed to delete outfit:', err);
    }
  };

  // Find wardrobe items by IDs to render inside outfit cards
  const getOutfitItems = (itemIds: string[]) => {
    return itemIds
      .map((id) => wardrobeItems.find((item) => item.id === id))
      .filter((item): item is WardrobeItem => !!item);
  };

  return (
    <SimpleGrid cols={{ base: 1, md: 12 }} spacing="lg">
      
      {/* Left panel: Outfit Generator Criteria */}
      <div className="grid-col-span-4">
        <Card className="bento-card" p="xl" radius="lg">
          <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="lg">
            AI Outfit Coordinator
          </Text>
          <Stack gap="md">
            <Select
              label="Occasion"
              data={['casual', 'business', 'formal', 'date night', 'travel']}
              value={occasion}
              onChange={setOccasion}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <Select
              label="Weather"
              data={['cold', 'mild', 'hot', 'rainy']}
              value={weather}
              onChange={setWeather}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <Select
              label="Vibe / Style"
              data={['minimalist', 'bold', 'classic', 'streetwear', 'cozy']}
              value={style}
              onChange={setStyle}
              variant="filled"
              classNames={{ input: 'elegant-text-input' }}
            />
            <Button
              onClick={generateOutfit}
              disabled={loading}
              color="amber"
              mt="md"
              leftSection={loading ? <Loader size="xs" color="white" /> : <IconSparkles size={16} />}
            >
              {loading ? 'Coordinating Outfit…' : 'Generate Outfit'}
            </Button>
          </Stack>
        </Card>
      </div>

      {/* Right panel: Outfit Recommendations List */}
      <div className="grid-col-span-8">
        <Card className="bento-card full-height-card" p="xl" radius="lg">
          <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="lg">
            Stylist Coordinates
          </Text>

          {outfits.length === 0 ? (
            <Stack align="center" justify="center" gap="xs" className="empty-state-section">
              <Text size="xl" className="editorial-title empty-state-title" c="dimmed">
                No coordinates generated.
              </Text>
              <Text size="xs" c="dimmed">
                Select occasion criteria on the left to compile AI looks.
              </Text>
            </Stack>
          ) : (
            <Stack gap="xl">
              {outfits.map((outfit) => {
                const items = getOutfitItems(outfit.item_ids);
                return (
                  <Card
                    key={outfit.id}
                    p="md"
                    radius="md"
                    className="outfit-coordinate-box"
                  >
                    <Group justify="space-between" align="flex-start" mb="xs">
                      <div>
                        <Text fw={600} size="md" c="amber">
                          {outfit.name}
                        </Text>
                        <Group gap="xs" mt={4}>
                          <Badge size="xs" variant="light" color="amber" leftSection={<IconCalendarEvent size={10} />}>
                            {outfit.occasion}
                          </Badge>
                        </Group>
                      </div>
                      
                      <Group gap="xs">
                        <ActionIcon
                          onClick={() => handleLogWorn(outfit.id)}
                          variant="light"
                          color="green"
                          radius="xl"
                          size="md"
                          title="Log worn"
                        >
                          <IconCheck size={14} />
                        </ActionIcon>
                        <ActionIcon
                          onClick={() => handleDeleteOutfit(outfit.id)}
                          variant="light"
                          color="red"
                          radius="xl"
                          size="md"
                          title="Delete outfit"
                        >
                          <IconTrash size={14} />
                        </ActionIcon>
                      </Group>
                    </Group>

                    <Text size="sm" c="dimmed" mb="md" fs="italic">
                      {outfit.ai_rationale}
                    </Text>

                    <Divider my="md" style={{ opacity: 0.5 }} />

                    {/* Outfit thumbnail list */}
                    <Group gap="md">
                      {items.length === 0 ? (
                        <Text size="xs" c="dimmed">Items no longer exist in closet inventory.</Text>
                      ) : (
                        items.map((item) => (
                          <Stack key={item.id} gap={4} align="center" className="outfit-thumbnail-container">
                            <Box
                              className="outfit-thumbnail-box"
                            >
                              <Image
                                src={`/${item.processed_image_path || item.original_image_path}`}
                                alt={item.subcategory || item.category}
                                w="100%"
                                h="100%"
                                fit="contain"
                              />
                            </Box>
                            <Text className="text-10" truncate="end" ta="center">
                              {item.brand || 'Minimalist'}
                            </Text>
                          </Stack>
                        ))
                      )}
                    </Group>
                  </Card>
                );
              })}
            </Stack>
          )}
        </Card>
      </div>

    </SimpleGrid>
  );
};
