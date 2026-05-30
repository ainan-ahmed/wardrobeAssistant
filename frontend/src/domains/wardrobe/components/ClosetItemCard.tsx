import React from 'react';
import { Card, Text, Image, Badge, Loader, ActionIcon, Flex, Stack, Group } from '@mantine/core';
import { WardrobeItem } from '../types';

interface ClosetItemCardProps {
  item: WardrobeItem;
  onDelete: (e: React.MouseEvent, id: string) => void;
  onClick?: (item: WardrobeItem) => void;
}

export const ClosetItemCard: React.FC<ClosetItemCardProps> = ({ item, onDelete, onClick }) => {
  return (
    <Card 
      p="md" 
      radius="md" 
      className={`closet-item-card ${onClick ? 'cursor-pointer' : ''}`}
      onClick={() => onClick?.(item)}
    >
      
      {/* Dynamic Status States */}
      {item.category === 'processing' ? (
        <Flex className="loader-container">
          <Loader size="sm" color="amber" mb="xs" />
          <Text size="xs" c="amber" fw={500} className="meta-label-upper">Isolating...</Text>
        </Flex>
      ) : item.category === 'failed' ? (
        <Flex className="loader-container" p="sm">
          <Text size="xs" color="red" fw={600} ta="center">Ingestion failed</Text>
          <Text size="10px" c="dimmed" mt={4} ta="center">Check logs</Text>
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
            className="card-trash-button"
          >
            🗑️
          </ActionIcon>

          {/* Centered Transparent Cutout Container */}
          <Card.Section 
            p="md" 
            className="card-image-box"
          >
            <Image
              src={`/${item.processed_image_path}`}
              alt={item.ai_description || 'Garment Cutout'}
              fallbackSrc="https://placehold.co/150"
              className="isolated-cutout card-image-file"
            />
          </Card.Section>

          <Stack gap={3} mt="sm">
            <Text size="xs" fw={700} className="meta-label-upper" truncate="end">
              {item.brand || 'Minimalist Brand'}
            </Text>
            <Text size="xs" c="dimmed" truncate="end">
              {item.subcategory || item.category}
            </Text>
            <Flex justify="space-between" align="center" mt={4}>
              <Group gap={4}>
                {item.colors.slice(0, 1).map((col, idx) => (
                  <Badge key={idx} variant="outline" size="xs" color="amber" className="text-10">
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
