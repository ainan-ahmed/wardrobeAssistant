import React from 'react';
import { Title, Text, Flex, ActionIcon, useMantineColorScheme, rem } from '@mantine/core';

export const AppHeader: React.FC = () => {
  const { colorScheme, toggleColorScheme } = useMantineColorScheme();

  return (
    <Flex 
      justify="space-between" 
      align="flex-end" 
      mb={45} 
      style={{ 
        borderBottom: '1px solid rgba(197, 138, 62, 0.15)', 
        paddingBottom: rem(25) 
      }}
    >
      <div>
        <Title order={1} className="editorial-title" style={{ fontSize: rem(42), fontWeight: 300, lineHeight: 1 }}>
          👗 wardrobe<span style={{ color: 'var(--amber-primary)', fontWeight: 400 }}>Assistant</span>
        </Title>
        <Text size="xs" c="dimmed" mt={8} style={{ letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          Local-first clothing background isolator & fashion vector assistant
        </Text>
      </div>
      <ActionIcon
        onClick={() => toggleColorScheme()}
        size="lg"
        variant="outline"
        color="amber"
        radius="99px"
        aria-label="Toggle Vibe Scheme"
        style={{ transition: 'var(--transition-smooth)' }}
      >
        {colorScheme === 'dark' ? '☀️' : '🌙'}
      </ActionIcon>
    </Flex>
  );
};
