import React, { useState, useEffect } from 'react';
import { MantineProvider, createTheme, Container, Tabs } from '@mantine/core';
import { FileWithPath } from '@mantine/dropzone';
import { IconHome, IconHanger, IconMessageCircle } from '@tabler/icons-react';
import axios from 'axios';

// Domain imports
import { WardrobeItem } from './domains/wardrobe/types';

// Shared imports
import { AppHeader } from './shared/components/AppHeader';

// Page-level tab components
import { HomeTab } from './pages/HomeTab';
import { WardrobeTab } from './pages/WardrobeTab';
import { AssistantTab } from './pages/AssistantTab';

// --- ELITE CUSTOM THEME CONFIGURATION ---
const theme = createTheme({
  fontFamily: 'Outfit, sans-serif',
  primaryColor: 'amber',
  colors: {
    amber: [
      '#FAF7F2', // 0: Cream Linen Light Base
      '#F4EFEA', // 1: Cream Panel Accent
      '#EFE8E0', // 2: Linen Active Border
      '#DECFA6', // 3: Soft Amber Gold
      '#C58A3E', // 4: Antique Gold
      '#A77330', // 5: Rich Ochre
      '#885C24', // 6: Primary Gold Accent
      '#694519', // 7: Dark Bronze
      '#4B3010', // 8: Dark Espresso
      '#2D1B07', // 9: Midnight Ochre
    ],
  },
  components: {
    Card: {
      defaultProps: {
        radius: 'md',
        withBorder: true,
      },
    },
    Button: {
      defaultProps: {
        radius: 'md',
      },
    },
  },
});

function MainApp() {
  const [loading, setLoading] = useState<boolean>(false);
  const [items, setItems] = useState<WardrobeItem[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchItems = async () => {
    try {
      let url = '/api/items/';
      const params: string[] = [];
      if (searchQuery.trim() !== '') {
        params.push(`search=${encodeURIComponent(searchQuery)}`);
      } else if (activeCategory !== 'All') {
        params.push(`category=${activeCategory.toLowerCase()}`);
      }

      if (params.length > 0) {
        url += `?${params.join('&')}`;
      }

      const response = await axios.get<WardrobeItem[]>(url);
      setItems(response.data);
    } catch (error) {
      console.error('Failed to fetch wardrobe items:', error);
    }
  };

  useEffect(() => {
    fetchItems();
    const interval = setInterval(fetchItems, 3500);
    return () => clearInterval(interval);
  }, [searchQuery, activeCategory]);

  const handleUpload = async (files: FileWithPath[], brand: string) => {
    if (files.length === 0) return;
    setLoading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', files[0]);
    if (brand.trim() !== '') {
      formData.append('brand', brand.trim());
    }

    try {
      await axios.post('/api/items/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      fetchItems();
    } catch (error: any) {
      console.error('Upload failed:', error);
      setUploadError(error.response?.data?.detail || 'Upload failed. Ensure server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!window.confirm('Remove this piece from your closet?')) return;
    try {
      await axios.delete(`/api/items/${id}`);
      fetchItems();
    } catch (error) {
      console.error('Failed to delete item:', error);
    }
  };

  const handleCategoryChange = (cat: string) => {
    setSearchQuery('');
    setActiveCategory(cat);
  };

  return (
    <Container size="lg" py="xl">
      <AppHeader />

      <Tabs defaultValue="home" keepMounted={false}>
        <Tabs.List mb="lg">
          <Tabs.Tab value="home" leftSection={<IconHome size={16} />}>
            Home
          </Tabs.Tab>
          <Tabs.Tab value="wardrobe" leftSection={<IconHanger size={16} />}>
            Wardrobe
          </Tabs.Tab>
          <Tabs.Tab value="assistant" leftSection={<IconMessageCircle size={16} />}>
            Stylist
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="home">
          <HomeTab
            items={items}
            loading={loading}
            uploadError={uploadError}
            searchQuery={searchQuery}
            activeCategory={activeCategory}
            onUpload={handleUpload}
            onSearchChange={setSearchQuery}
            onCategoryChange={handleCategoryChange}
            onDelete={handleDelete}
          />
        </Tabs.Panel>

        <Tabs.Panel value="wardrobe">
          <WardrobeTab
            items={items}
            searchQuery={searchQuery}
            activeCategory={activeCategory}
            onSearchChange={setSearchQuery}
            onCategoryChange={handleCategoryChange}
            onDelete={handleDelete}
          />
        </Tabs.Panel>

        <Tabs.Panel value="assistant">
          <AssistantTab />
        </Tabs.Panel>
      </Tabs>
    </Container>
  );
}

export default function App() {
  return (
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <MainApp />
    </MantineProvider>
  );
}

