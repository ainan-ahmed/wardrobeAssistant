import React from 'react';
import { SimpleGrid } from '@mantine/core';
import { FileWithPath } from '@mantine/dropzone';
import { WardrobeItem } from '../domains/wardrobe/types';
import { ClosetInsights } from '../domains/wardrobe/components/ClosetInsights';
import { ApparelIngestion } from '../domains/wardrobe/components/ApparelIngestion';
import { ClosetInventory } from '../domains/wardrobe/components/ClosetInventory';

interface HomeTabProps {
  items: WardrobeItem[];
  loading: boolean;
  uploadError: string | null;
  searchQuery: string;
  activeCategory: string;
  onUpload: (files: FileWithPath[], brand: string) => void;
  onSearchChange: (val: string) => void;
  onCategoryChange: (cat: string) => void;
  onDelete: (e: React.MouseEvent, id: string) => void;
}

export const HomeTab: React.FC<HomeTabProps> = ({
  items, loading, uploadError, searchQuery, activeCategory,
  onUpload, onSearchChange, onCategoryChange, onDelete,
}) => {
  const totalItemsCount = items.filter(
    (i) => i.category !== 'processing' && i.category !== 'failed'
  ).length;

  return (
    <SimpleGrid cols={{ base: 1, md: 12 }} spacing="lg">
      {/* Left column: Insights + Upload */}
      <div style={{ gridColumn: 'span 4' }}>
        <SimpleGrid cols={1} spacing="lg">
          <ClosetInsights totalItemsCount={totalItemsCount} />
          <ApparelIngestion
            onUpload={onUpload}
            loading={loading}
            uploadError={uploadError}
          />
        </SimpleGrid>
      </div>

      {/* Right column: Recent items preview */}
      <div style={{ gridColumn: 'span 8' }}>
        <ClosetInventory
          items={items.slice(0, 9)}
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
          activeCategory={activeCategory}
          onCategoryChange={onCategoryChange}
          onDelete={onDelete}
        />
      </div>
    </SimpleGrid>
  );
};
