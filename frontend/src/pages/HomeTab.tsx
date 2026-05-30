import React, { useMemo } from 'react';
import {
  SimpleGrid, Card, Text, Paper, Group, Image, Stack, RingProgress, Badge,
} from '@mantine/core';
import { FileWithPath } from '@mantine/dropzone';
import { WardrobeItem } from '../domains/wardrobe/types';
import { ApparelIngestion } from '../domains/wardrobe/components/ApparelIngestion';

interface HomeTabProps {
  items: WardrobeItem[];
  loading: boolean;
  uploadError: string | null;
  onUpload: (files: FileWithPath[], brand: string) => void;
}

/** Derive analytics from the item list */
function useWardrobeStats(items: WardrobeItem[]) {
  return useMemo(() => {
    const active = items.filter((i) => i.category !== 'processing' && i.category !== 'failed');
    const total = active.length;

    // Category breakdown
    const categoryMap: Record<string, number> = {};
    active.forEach((i) => {
      const cat = i.category || 'uncategorized';
      categoryMap[cat] = (categoryMap[cat] || 0) + 1;
    });
    const categories = Object.entries(categoryMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);

    // Top colors
    const colorMap: Record<string, number> = {};
    active.forEach((i) => i.colors?.forEach((c) => {
      colorMap[c] = (colorMap[c] || 0) + 1;
    }));
    const topColors = Object.entries(colorMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    // Top style tags
    const tagMap: Record<string, number> = {};
    active.forEach((i) => i.style_tags?.forEach((t) => {
      tagMap[t] = (tagMap[t] || 0) + 1;
    }));
    const topTags = Object.entries(tagMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);

    // Brand count
    const brands = new Set(active.map((i) => i.brand).filter(Boolean)).size;

    // Recent 5
    const recent = active.slice(-5).reverse();

    return { total, categories, topColors, topTags, brands, recent };
  }, [items]);
}

// Palette for the ring chart segments
const RING_COLORS = ['#C58A3E', '#A77330', '#885C24', '#DECFA6', '#694519', '#4B3010'];

export const HomeTab: React.FC<HomeTabProps> = ({
  items, loading, uploadError, onUpload,
}) => {
  const stats = useWardrobeStats(items);

  return (
    <SimpleGrid cols={{ base: 1, md: 12 }} spacing="lg">

      {/* ── Left column: Upload + Quick Stats ── */}
      <div style={{ gridColumn: 'span 4' }}>
        <Stack gap="lg">
          {/* Upload */}
          <ApparelIngestion onUpload={onUpload} loading={loading} uploadError={uploadError} />

          {/* Quick stats */}
          <Card className="bento-card" p="xl" radius="lg">
            <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="md">
              Closet Overview
            </Text>
            <SimpleGrid cols={2} spacing="md">
              <StatTile label="Total Pieces" value={stats.total} />
              <StatTile label="Brands" value={stats.brands} />
              <StatTile label="Categories" value={stats.categories.length} />
              <StatTile label="Color Palette" value={stats.topColors.length} />
            </SimpleGrid>
          </Card>
        </Stack>
      </div>

      {/* ── Right column: Dashboard analytics ── */}
      <div style={{ gridColumn: 'span 8' }}>
        <Stack gap="lg">

          {/* Category breakdown ring + list */}
          <Card className="bento-card" p="xl" radius="lg">
            <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="lg">
              Category Breakdown
            </Text>
            {stats.total === 0 ? (
              <Text c="dimmed" size="sm" ta="center" py="xl">
                Upload items to see your wardrobe breakdown.
              </Text>
            ) : (
              <Group align="center" gap="xl">
                <RingProgress
                  size={140}
                  thickness={14}
                  roundCaps
                  sections={stats.categories.map(([, count], i) => ({
                    value: (count / stats.total) * 100,
                    color: RING_COLORS[i % RING_COLORS.length],
                  }))}
                  label={
                    <Text ta="center" fw={700} size="lg">
                      {stats.total}
                    </Text>
                  }
                />
                <Stack gap="xs" style={{ flex: 1 }}>
                  {stats.categories.map(([cat, count], i) => (
                    <Group key={cat} justify="space-between">
                      <Group gap="xs">
                        <div
                          style={{
                            width: 10, height: 10, borderRadius: '50%',
                            backgroundColor: RING_COLORS[i % RING_COLORS.length],
                          }}
                        />
                        <Text size="sm" tt="capitalize">{cat}</Text>
                      </Group>
                      <Text size="sm" c="dimmed">{count}</Text>
                    </Group>
                  ))}
                </Stack>
              </Group>
            )}
          </Card>

          {/* Style DNA + Top Colors */}
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
            <Card className="bento-card" p="xl" radius="lg">
              <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="md">
                Style DNA
              </Text>
              {stats.topTags.length === 0 ? (
                <Text c="dimmed" size="sm">No style data yet.</Text>
              ) : (
                <Group gap="xs">
                  {stats.topTags.map(([tag]) => (
                    <Badge key={tag} variant="light" color="amber" radius="sm" size="md">
                      {tag}
                    </Badge>
                  ))}
                </Group>
              )}
            </Card>

            <Card className="bento-card" p="xl" radius="lg">
              <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="md">
                Dominant Colors
              </Text>
              {stats.topColors.length === 0 ? (
                <Text c="dimmed" size="sm">No color data yet.</Text>
              ) : (
                <Group gap="sm">
                  {stats.topColors.map(([color, count]) => (
                    <Stack key={color} gap={4} align="center">
                      <div
                        style={{
                          width: 36, height: 36, borderRadius: 8,
                          backgroundColor: color,
                          border: '2px solid var(--mantine-color-default-border)',
                        }}
                      />
                      <Text size="xs" c="dimmed">{count}</Text>
                    </Stack>
                  ))}
                </Group>
              )}
            </Card>
          </SimpleGrid>

          {/* Recent additions */}
          <Card className="bento-card" p="xl" radius="lg">
            <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="md">
              Recent Additions
            </Text>
            {stats.recent.length === 0 ? (
              <Text c="dimmed" size="sm" ta="center" py="md">
                Your recent uploads will appear here.
              </Text>
            ) : (
              <Group gap="md">
                {stats.recent.map((item) => (
                  <Image
                    key={item.id}
                    src={item.processed_image_path || item.original_image_path}
                    alt={item.ai_description || item.category}
                    w={72}
                    h={72}
                    radius="md"
                    fit="cover"
                    style={{ border: '1px solid var(--mantine-color-default-border)' }}
                  />
                ))}
              </Group>
            )}
          </Card>

        </Stack>
      </div>
    </SimpleGrid>
  );
};

/** Small stat tile */
const StatTile: React.FC<{ label: string; value: number | string }> = ({ label, value }) => (
  <Paper
    p="md"
    radius="md"
    className="closet-stat-tile"
  >
    <Text size="xs" c="dimmed" fw={500}>{label}</Text>
    <Text size="xl" fw={700} c="amber" mt={2}>{value}</Text>
  </Paper>
);
