import React, { useMemo } from 'react';
import { Card, Text, Title, SimpleGrid, Group, Progress, Stack, Badge, Image, Box } from '@mantine/core';
import { WardrobeItem } from '../domains/wardrobe/types';
import { IconChartPie, IconTrendingUp, IconTrendingDown } from '@tabler/icons-react';

interface AnalyticsTabProps {
  wardrobeItems: WardrobeItem[];
}

export const AnalyticsTab: React.FC<AnalyticsTabProps> = ({ wardrobeItems }) => {
  const activeItems = useMemo(() => wardrobeItems.filter(item => item.category !== 'processing' && item.category !== 'failed'), [wardrobeItems]);

  const { mostWorn, leastWorn } = useMemo(() => {
    const sorted = [...activeItems].sort((a, b) => b.times_worn - a.times_worn);
    return {
      mostWorn: sorted.slice(0, 5),
      leastWorn: sorted.slice(-5).reverse(), // Show absolute least worn
    };
  }, [activeItems]);

  const colorStats = useMemo(() => {
    const counts: Record<string, number> = {};
    activeItems.forEach(item => {
      item.colors.forEach(color => {
        const lower = color.toLowerCase();
        counts[lower] = (counts[lower] || 0) + 1;
      });
    });

    const totalColors = Object.values(counts).reduce((a, b) => a + b, 0);
    const sortedColors = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([color, count]) => ({
        color,
        count,
        percentage: totalColors > 0 ? (count / totalColors) * 100 : 0
      }));

    return sortedColors;
  }, [activeItems]);

  const getColorHex = (colorName: string) => {
    const map: Record<string, string> = {
      black: '#212529',
      white: '#f8f9fa',
      gray: '#adb5bd',
      grey: '#adb5bd',
      navy: '#1864ab',
      blue: '#339af0',
      red: '#fa5252',
      green: '#40c057',
      yellow: '#fcc419',
      brown: '#8b4513',
      beige: '#f1f3f5',
      pink: '#f06595',
      purple: '#845ef7',
      orange: '#fd7e14',
      cream: '#fffdd0',
      tan: '#d2b48c',
      khaki: '#c3b091',
    };
    return map[colorName.toLowerCase()] || '#ced4da';
  };

  const ItemList = ({ title, icon: Icon, items }: { title: string, icon: any, items: WardrobeItem[] }) => (
    <Card shadow="sm" p="lg" radius="md" withBorder>
      <Group mb="md">
        <Icon size={24} />
        <Title order={3}>{title}</Title>
      </Group>
      {items.length === 0 ? (
        <Text c="dimmed">Not enough data.</Text>
      ) : (
        <Stack gap="sm">
          {items.map((item) => (
            <Group key={item.id} wrap="nowrap">
              <Image 
                src={`/backend/data/processed/${item.id}_processed.png`} 
                h={50} w={50} fit="contain" 
                fallbackSrc="https://placehold.co/50x50?text=No+Image"
                radius="sm"
              />
              <Box style={{ flex: 1 }}>
                <Text size="sm" fw={500} lineClamp={1}>{item.ai_description || item.subcategory}</Text>
                <Text size="xs" c="dimmed">{item.brand || 'No brand'}</Text>
              </Box>
              <Badge variant="light" color={title.includes('Most') ? 'green' : 'red'}>
                {item.times_worn} wears
              </Badge>
            </Group>
          ))}
        </Stack>
      )}
    </Card>
  );

  return (
    <Stack gap="xl">
      <Card shadow="sm" p="lg" radius="md" withBorder>
        <Group mb="md">
          <IconChartPie size={24} />
          <Title order={3}>Wardrobe Color Palette</Title>
        </Group>
        
        {colorStats.length > 0 ? (
          <Box>
            <Progress.Root size="xl" radius="xl" mb="md">
              {colorStats.map((stat) => (
                <Progress.Section 
                  key={stat.color} 
                  value={stat.percentage} 
                  color={getColorHex(stat.color)}
                >
                  <Progress.Label c={['white', 'cream', 'beige', 'yellow'].includes(stat.color.toLowerCase()) ? 'black' : 'white'}>
                    {stat.percentage > 10 ? stat.color : ''}
                  </Progress.Label>
                </Progress.Section>
              ))}
            </Progress.Root>
            <Group gap="xs">
              {colorStats.map(stat => (
                <Badge key={stat.color} variant="dot" color={getColorHex(stat.color)} size="sm">
                  {stat.color} ({Math.round(stat.percentage)}%)
                </Badge>
              ))}
            </Group>
          </Box>
        ) : (
          <Text c="dimmed">No color data available.</Text>
        )}
      </Card>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
        <ItemList title="Most Worn (Hero Items)" icon={IconTrendingUp} items={mostWorn} />
        <ItemList title="Least Worn (Dead Weight)" icon={IconTrendingDown} items={leastWorn} />
      </SimpleGrid>
    </Stack>
  );
};
