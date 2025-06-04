# Vendor Portal Application

## Application Structure

This application follows a structured organization with a common layout that includes a sidebar for navigation between different modules:

### Main Components

- **MainLayout**: Provides the sidebar navigation and overall application structure
- **VendorDashboard**: Product management dashboard
- **VendorOrdersDashboard**: Order management and fulfillment
- **ImagesPage**: Image upload and enhancement for product listings

### Navigation Flow

The application uses React Router for navigation between different sections:

- `/dashboard` - Product management
- `/orders` - Order management
- `/images` - Image upload and processing
- Other sections (Analytics, Shipping, Settings) are placeholders for future development

### Authentication

The application includes:
- Login page (`/login`)
- Registration page (`/register`)
- Authentication guard to protect routes

## Setup Instructions

1. Create the folder structure:
   ```
   mkdir -p src/components/layout
   ```

2. Move the provided components to their respective folders:
   - Place `MainLayout.tsx` in `src/components/layout/`
   - Place `PageHeader.tsx` in `src/components/layout/`
   - Place `ImagesPage.tsx` in `src/components/images/`
   - Update the imports in existing files as needed

3. Update your `App.tsx` file with the new routing structure

4. Run the application:
   ```
   npm run dev
   ```

## Development Guidelines

When adding new features:

1. Create components within the appropriate feature folder
2. Use the `PageHeader` component for consistent headers
3. Add routes to `App.tsx` inside the `MainLayout` route
4. Update the navigation items in `MainLayout.tsx` if adding major new sections

## Future Enhancements

- Add analytics dashboard
- Add shipping management
- Implement settings page
- Add user management for multi-user vendors