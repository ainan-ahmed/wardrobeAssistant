import React, { useState } from 'react';
import { Card, Text, TextInput, SimpleGrid, Flex, Group, Badge } from '@mantine/core';
import { ClosetItemCard } from './ClosetItemCard';
import { ClosetItemDrawer } from './ClosetItemDrawer';
import { WardrobeItem } from '../types';

interface ClosetInventoryProps {
  items: WardrobeItem[];
  searchQuery: string;
  onSearchChange: (val: string) => void;
  activeCategory: string;
  onCategoryChange: (cat: string) => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
  onUpdate?: () => void;
}

export const ClosetInventory: React.FC<ClosetInventoryProps> = ({
  items,
  searchQuery,
  onSearchChange,
  activeCategory,
  onCategoryChange,
  onDelete,
  onUpdate
}) => {
  const [selectedItem, setSelectedItem] = useState<WardrobeItem | null>(null);
  const [drawerOpened, setDrawerOpened] = useState(false);

  const handleCardClick = (item: WardrobeItem) => {
    setSelectedItem(item);
    setDrawerOpened(true);
  };

  const handleDrawerClose = () => {
    setDrawerOpened(false);
    setSelectedItem(null);
  };

  return (
    <Card className="bento-card full-height-card" p="xl" radius="lg">
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
          className="elegant-search-wrapper"
          classNames={{ input: 'elegant-search-input' }}
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
            className={activeCategory === cat ? 'elegant-inventory-pill elegant-inventory-pill-active' : 'elegant-inventory-pill'}
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
          className="empty-state-section"
        >
          <Text size="xl" className="editorial-title empty-state-title" c="dimmed">
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
              onClick={handleCardClick}
            />
          ))}
        </SimpleGrid>
      )}

      {/* Item Profile Details Slide-out Drawer */}
      <ClosetItemDrawer
        item={selectedItem}
        opened={drawerOpened}
        onClose={handleDrawerClose}
        onUpdate={onUpdate || (() => {})}
        onDelete={onDelete}
      />
    </Card>
  );
};
