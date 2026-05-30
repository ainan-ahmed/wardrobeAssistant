import React from 'react';
import { Card, Text, Image, Badge, Loader, ActionIcon, Flex, Stack, Group, rem } from '@mantine/core';
import { WardrobeItem } from '../types';

interface ClosetItemCardProps {
  item: WardrobeItem;
  onDelete: (e: React.MouseEvent, id: string) => void;
}

export const ClosetItemCard: React.FC<ClosetItemCardProps> = ({ item, onDelete }) => {
  return (
    <Card 
      p="md" 
      radius="md" 
      style={{ 
        position: 'relative', 
        overflow: 'visible',
        border: '1px solid rgba(220, 215, 206, 0.4)',
        backgroundColor: 'rgba(255, 255, 255, 0.3)',
        transition: 'var(--transition-smooth)',
      }}
      className="closet-item-card"
    >
      
      {/* Dynamic Status States */}
      {item.category === 'processing' ? (
        <Flex justify="center" align="center" style={{ minHeight: rem(160), flexDirection: 'column' }}>
          <Loader size="sm" color="amber" mb="xs" />
          <Text size="xs" c="amber" fw={500} style={{ letterSpacing: '0.05em' }}>Isolating...</Text>
        </Flex>
      ) : item.category === 'failed' ? (
        <Flex justify="center" align="center" style={{ minHeight: rem(160), flexDirection: 'column', padding: rem(10) }}>
          <Text size="xs" color="red" fw={600} style={{ textAlign: 'center' }}>Ingestion failed</Text>
          <Text size="10px" c="dimmed" mt={4} style={{ textAlign: 'center' }}>Check logs</Text>
        </Flex>
      ) : (
        <>
          {/* Elegant Trash Icon on Hover */}
          <ActionIcon
            onClick={(e) => onDelete(e, item.id)}
            variant="filled"
            color="red"
            size="sm"
            radius="99px"
            style={{
              position: 'absolute',
              top: rem(-8),
              right: rem(-8),
              zIndex: 10,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}
          >
            🗑️
          </ActionIcon>

          {/* Centered Transparent Cutout Container */}
          <Card.Section 
            p="md" 
            style={{ 
              backgroundColor: 'var(--panel-cream)', 
              borderRadius: 'var(--mantine-radius-md)',
              display: 'flex', 
              justifyContent: 'center',
              alignItems: 'center',
              minHeight: rem(160)
            }}
          >
            <Image
              src={`/${item.processed_image_path}`}
              alt={item.ai_description || 'Garment Cutout'}
              fallbackSrc="https://placehold.co/150"
              className="isolated-cutout"
              style={{
                maxHeight: rem(140),
                objectFit: 'contain',
                transition: 'transform 0.4s ease',
              }}
            />
          </Card.Section>

          <Stack gap={3} mt="sm">
            <Text size="xs" fw={700} style={{ letterSpacing: '0.02em', textTransform: 'uppercase' }} truncate="end">
              {item.brand || 'Minimalist Brand'}
            </Text>
            <Text size="xs" c="dimmed" truncate="end">
              {item.subcategory || item.category}
            </Text>
            <Flex justify="space-between" align="center" mt={4}>
              <Group gap={4}>
                {item.colors.slice(0, 1).map((col, idx) => (
                  <Badge key={idx} variant="outline" size="xs" color="amber" style={{ fontSize: '10px' }}>
                    {col}
                  </Badge>
                ))}
              </Group>
              <Text size="10px" c="dimmed" fw={500}>
                Worn: {item.times_worn}
              </Text>
            </Flex>
          </Stack>
        </>
      )}
    </Card>
  );
};
