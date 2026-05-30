import React from 'react';
import { Card, Text, TextInput, SimpleGrid, Flex, Group, Badge, rem } from '@mantine/core';
import { ClosetItemCard } from './ClosetItemCard';
import { WardrobeItem } from '../types';

interface ClosetInventoryProps {
  items: WardrobeItem[];
  searchQuery: string;
  onSearchChange: (val: string) => void;
  activeCategory: string;
  onCategoryChange: (cat: string) => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
}

export const ClosetInventory: React.FC<ClosetInventoryProps> = ({
  items,
  searchQuery,
  onSearchChange,
  activeCategory,
  onCategoryChange,
  onDelete
}) => {
  return (
    <Card className="bento-card" p="xl" radius="lg" style={{ minHeight: '100%' }}>
      {/* CLOSET HEADER & SEARCH */}
      <Flex justify="space-between" align="center" direction={{ base: 'column', sm: 'row' }} gap="md" mb="lg">
        <Text className="editorial-header" size="xs" c="dimmed" fw={700}>
          Closet Inventory
        </Text>
        
        {/* Elegant Semantic Search Bar */}
        <TextInput
          placeholder="🔍 Search semantically (e.g. 'cozy warm layers')"
          value={searchQuery}
          onChange={(event) => onSearchChange(event.currentTarget.value)}
          style={{ width: rem(300) }}
          styles={{
            input: {
              borderRadius: rem(99),
              border: '1px solid rgba(197, 138, 62, 0.25)',
              backgroundColor: 'rgba(255, 255, 255, 0.4)',
              paddingLeft: rem(35),
              '&:focus': {
                borderColor: 'var(--amber-primary)',
                boxShadow: '0 0 0 1px var(--amber-primary)'
              }
            }
          }}
        />
      </Flex>

      {/* FILTER PILLS */}
      <Group gap="xs" mb="xl">
        {['All', 'Tops', 'Bottoms', 'Shoes', 'Outerwear', 'Accessories'].map((cat) => (
          <Badge
            key={cat}
            onClick={() => onCategoryChange(cat)}
            variant={activeCategory === cat ? 'filled' : 'outline'}
            color="amber"
            radius="99px"
            style={{
              cursor: 'pointer',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              padding: `${rem(6)} ${rem(14)}`,
              height: 'auto',
              border: activeCategory === cat ? 'none' : '1px solid rgba(197, 138, 62, 0.4)',
              transition: 'var(--transition-smooth)'
            }}
          >
            {cat}
          </Badge>
        ))}
      </Group>

      {/* INVENTORY GRID */}
      {items.length === 0 ? (
        <Flex 
          justify="center" 
          align="center" 
          direction="column" 
          style={{ minHeight: 350 }}
        >
          <Text size="xl" className="editorial-title" c="dimmed" style={{ fontSize: rem(28) }}>
            Your digital boutique is empty.
          </Text>
          <Text size="xs" c="dimmed" mt={8}>
            Start by uploading high-quality photos on the left bento panel.
          </Text>
        </Flex>
      ) : (
        <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="lg">
          {items.map((item) => (
            <ClosetItemCard 
              key={item.id} 
              item={item} 
              onDelete={onDelete} 
            />
          ))}
        </SimpleGrid>
      )}
    </Card>
  );
};
