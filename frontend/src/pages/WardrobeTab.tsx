import React from 'react';
import { WardrobeItem } from '../domains/wardrobe/types';
import { ClosetInventory } from '../domains/wardrobe/components/ClosetInventory';

interface WardrobeTabProps {
  items: WardrobeItem[];
  searchQuery: string;
  activeCategory: string;
  onSearchChange: (val: string) => void;
  onCategoryChange: (cat: string) => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
  onUpdate?: () => void;
}

export const WardrobeTab: React.FC<WardrobeTabProps> = ({
  items, searchQuery, activeCategory,
  onSearchChange, onCategoryChange, onDelete, onUpdate,
}) => {
  return (
    <ClosetInventory
      items={items}
      searchQuery={searchQuery}
      onSearchChange={onSearchChange}
      activeCategory={activeCategory}
      onCategoryChange={onCategoryChange}
      onDelete={onDelete}
      onUpdate={onUpdate}
    />
  );
};
