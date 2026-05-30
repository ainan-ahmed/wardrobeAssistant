import React from 'react';
import { Card, Text, SimpleGrid, Paper } from '@mantine/core';

interface ClosetInsightsProps {
  totalItemsCount: number;
}

export const ClosetInsights: React.FC<ClosetInsightsProps> = ({ totalItemsCount }) => {
  return (
    <Card className="bento-card" p="xl" radius="lg">
      <Text className="editorial-header" size="xs" c="dimmed" fw={700} mb="md">
        Closet Insights
      </Text>
      <SimpleGrid cols={2} spacing="md">
        <Paper p="md" radius="md" style={{ backgroundColor: 'var(--amber-glow)', border: '1px solid rgba(197, 138, 62, 0.1)' }}>
          <Text size="xs" c="dimmed" fw={500}>Apparel Owned</Text>
          <Text size="2xl" fw={700} c="amber" mt={2}>{totalItemsCount}</Text>
        </Paper>
        <Paper p="md" radius="md" style={{ backgroundColor: 'var(--amber-glow)', border: '1px solid rgba(197, 138, 62, 0.1)' }}>
          <Text size="xs" c="dimmed" fw={500}>Styling Vibe</Text>
          <Text size="sm" fw={700} c="amber" mt={6} truncate="end">Warm Minimalist</Text>
        </Paper>
      </SimpleGrid>
    </Card>
  );
};
