import { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  ArrowDownWideNarrow, ArrowLeft, ArrowRight, Bell, BookOpen, Check, CheckCheck,
  ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Heart, House, LayoutGrid,
  Menu, Minus, Moon, PackageSearch, Plus, Search, Settings, ShoppingBag, ShoppingCart,
  Languages, SlidersHorizontal, Sparkles,
  Store, Sun, Trash2, UserRound, X,
} from 'lucide-react'
import { adminHeaders, api } from './api.js'

const words = {
  en: {
    announcement: 'Thoughtful finds. Delivered with care.',
    shop: 'Shop', story: 'Our promise', help: 'Help', search: 'Search products...',
    heroEyebrow: 'A better way to shop',
    heroTitle: 'Good things, found here.',
    heroBody: 'Hikma Online Shopping — Shop Smart, Buy Easy, Save More.',
    explore: 'Explore collection', curated: 'Curated for everyday',
    all: 'All products', sort: 'Sort by', newest: 'Newest', low: 'Price: low to high',
    high: 'Price: high to low', inStock: 'In stock only', noProducts: 'Nothing here yet',
    noProductsBody: 'Try another search or category. New finds are on the way.',
    add: 'Add to bag', details: 'View details', soldOut: 'Sold out',
    bag: 'Your bag', emptyBag: 'Your bag is waiting', emptyBagBody: 'Find something you love and make it yours.',
    subtotal: 'Subtotal', deliveryNote: 'Delivery fee confirmed with you before dispatch.',
    checkout: 'Continue to checkout', yourDetails: 'Delivery details', fullName: 'Full name',
    phone: 'Phone number', city: 'City', address: 'Delivery address', payment: 'Payment method',
    cash: 'Cash on delivery', telebirr: 'Telebirr', cbe: 'CBE Birr / Bank',
    placeOrder: 'Place order', placing: 'Placing order…', backToBag: 'Back to bag',
    orderSuccess: 'Order received', orderSuccessBody: 'We’ll contact you to confirm delivery.',
    orderNumber: 'Order number', close: 'Continue browsing',
    tracking: 'Track order', trackTitle: 'Where is my order?', trackAction: 'Find my order',
    trackingResult: 'Current status', trackingHelp: 'Enter your order number or checkout phone.',
    support: 'Contact us', supportTitle: 'How can we help?', sendMessage: 'Send a message',
    faqs: 'A few good questions', shippingQ: 'How does delivery work?',
    shippingA: 'We confirm the delivery fee and timing with you before dispatch.',
    paymentQ: 'Which payment options are available?',
    paymentA: 'Choose Telebirr, CBE Birr / bank, or cash on delivery at checkout.',
    returnsQ: 'Can I ask about an order?', returnsA: 'Yes — share your order number and phone in the tracker or contact our team.',
    promiseTitle: 'A little more care, in every order.',
    promiseBody: 'Thoughtfully selected essentials, honest prices, and a real person ready to help.',
    supportName: 'Your name', supportMessage: 'Tell us what you need', send: 'Send inquiry',
    sent: 'Thanks — your message is with our team.', footer: 'Made for everyday living.',
    saved: 'Saved', remove: 'Remove', quantity: 'Quantity', category: 'Category',
    admin: 'Store admin', signIn: 'Sign in', token: 'Admin access token',
    dashboard: 'Overview', products: 'Products', orders: 'Orders', revenue: 'Revenue',
    pending: 'Pending', manageProducts: 'Manage products', addProduct: 'Add product',
    editProduct: 'Edit product', nameEn: 'Product name (English)', nameAm: 'Product name (Amharic)',
    descriptionEn: 'Description (English)', descriptionAm: 'Description (Amharic)',
    price: 'Price (ETB)', stock: 'Stock quantity', saveProduct: 'Save product',
    uploadHint: 'Drop photos here or click to upload (up to 10)', status: 'Update status',
    customer: 'Customer', total: 'Total', signOut: 'Sign out', adminLoginError: 'Could not verify access token',
    openMenu: 'Open menu', favorites: 'Wishlist', language: 'Language',
    home: 'Home', categories: 'Categories', menu: 'Menu', profile: 'Profile',
    settings: 'Settings', notifications: 'Notifications', markAllRead: 'Mark all read',
    allCaughtUp: 'You’re all caught up', noActivity: 'Order updates will appear here.',
    storeNotice: 'Store notice', newArrivals: 'New arrivals & offers',
    newArrivalsBody: 'Discover new products and any current offers in the collection.',
    orderPlacedNotice: 'Your order was received', orderStatusNotice: 'Order status updated',
    orderCount: 'Orders', savedItems: 'Saved items', bagSummary: 'Bag items',
    guestName: 'Welcome to Hikma', profileDetails: 'Your shopping overview',
    notificationSettings: 'Notifications & alerts', enableNotifications: 'Enable order and store alerts',
    clearReadNotifications: 'Clear read notifications', appearance: 'Appearance',
    lightMode: 'Light mode', darkMode: 'Dark mode', storePreferences: 'Shopping & display preferences',
    clearShoppingData: 'Clear bag and browsing history', confirmClearStore: 'Clear your bag, recent views, and search history?',
    shoppingDataCleared: 'Bag and browsing history cleared.', recentViewed: 'Recently viewed',
    recentSearches: 'Recent searches', languageAmharic: 'አማርኛ', languageEnglish: 'English',
    openSettings: 'Open settings', adminLink: 'Store admin', notificationCount: 'unread notifications',
    unread: 'unread', chooseCategory: 'Choose a category', categoryAll: 'All products',
    supportFaq: 'Support & FAQs', accountInfo: 'Telegram profile',
    storeNavigation: 'Store navigation', dismiss: 'Close', noCategories: 'Categories will appear here.',
    footerShop: 'Explore', footerHelp: 'Help & support', footerPreferences: 'Preferences',
    addToWishlist: 'Add to wishlist', removeFromWishlist: 'Remove from wishlist',
    primaryNavigation: 'Main navigation', menuAction: 'MENU',
  },
  am: {
    announcement: 'በጥንቃቄ የተመረጡ ዕቃዎች፣ በእንክብካቤ ይደርሳሉ።',
    shop: 'ይግዙ', story: 'ስለ እኛ', help: 'እገዛ', search: 'ዕቃዎችን እዚህ ይፈልጉ...',
    heroEyebrow: 'በተሻለ መንገድ ይግዙ',
    heroTitle: 'የሚወዷቸው እቃዎች እዚህ አሉ።',
    heroBody: 'ሂክማ ኦንላይን ሾፒንግ — በጥበብ ይግዙ፣ በቀላሉ ይቀበሉ።',
    explore: 'ምርቶችን ይመልከቱ', curated: 'ለዕለት ተዕለት የተመረጡ',
    all: 'ሁሉም ምርቶች', sort: 'ደርድር', newest: 'አዳዲስ', low: 'ዋጋ፡ ከዝቅተኛ',
    high: 'ዋጋ፡ ከከፍተኛ', inStock: 'በክምችት ያሉ', noProducts: 'ምንም ምርት አልተገኘም',
    noProductsBody: 'ሌላ ፍለጋ ወይም ምድብ ይሞክሩ።',
    add: 'ወደ ቦርሳ ጨምር', details: 'ዝርዝር ይመልከቱ', soldOut: 'አልቋል',
    bag: 'የግዢ ቦርሳ', emptyBag: 'ቦርሳዎ ባዶ ነው', emptyBagBody: 'የሚወዱትን ይምረጡና ይግዙ።',
    subtotal: 'ድምር', deliveryNote: 'የማድረሻ ክፍያን ከመላካችን በፊት እናሳውቅዎታለን።',
    checkout: 'ወደ ክፍያ ይቀጥሉ', yourDetails: 'የማድረሻ መረጃ', fullName: 'ሙሉ ስም',
    phone: 'ስልክ ቁጥር', city: 'ከተማ', address: 'የማድረሻ አድራሻ', payment: 'የክፍያ ዘዴ',
    cash: 'በማድረስ ጊዜ ክፍያ', telebirr: 'ቴሌብር', cbe: 'ሲቢኢ ብር / ባንክ',
    placeOrder: 'ትዕዛዝ ይላኩ', placing: 'ትዕዛዝ በመላክ ላይ…', backToBag: 'ወደ ቦርሳ ተመለስ',
    orderSuccess: 'ትዕዛዝዎ ደርሶናል', orderSuccessBody: 'ማድረሻውን ለማረጋገጥ እናገኝዎታለን።',
    orderNumber: 'የትዕዛዝ ቁጥር', close: 'ግዢዎን ይቀጥሉ',
    tracking: 'ትዕዛዝ ይከታተሉ', trackTitle: 'ትዕዛዜ የት ደረሰ?', trackAction: 'ትዕዛዜን ፈልግ',
    trackingResult: 'የአሁኑ ሁኔታ', trackingHelp: 'የትዕዛዝ ቁጥር ወይም የግዢ ስልክ ቁጥር ያስገቡ።',
    support: 'ያግኙን', supportTitle: 'እንዴት እንርዳዎ?', sendMessage: 'መልዕክት ይላኩ',
    faqs: 'ብዙ ጊዜ የሚጠየቁ ጥያቄዎች', shippingQ: 'ማድረስ እንዴት ይሰራል?',
    shippingA: 'ከመላካችን በፊት የማድረሻ ዋጋና ጊዜ እናረጋግጣለን።',
    paymentQ: 'ምን የክፍያ ዘዴዎች አሉ?', paymentA: 'ቴሌብር፣ ሲቢኢ ብር/ባንክ ወይም በማድረስ ጊዜ ይምረጡ።',
    returnsQ: 'ስለ ትዕዛዝ መጠየቅ እችላለሁ?', returnsA: 'አዎ፣ ቁጥርና ስልክ በመከታተያው ያስገቡ ወይም ያግኙን።',
    promiseTitle: 'በእያንዳንዱ ትዕዛዝ ተጨማሪ እንክብካቤ።',
    promiseBody: 'በጥንቃቄ የተመረጡ እቃዎች፣ ተመጣጣኝ ዋጋና ለመርዳት ዝግጁ ሰው።',
    supportName: 'ስምዎ', supportMessage: 'ምን እንድንረዳዎ ይጻፉ', send: 'ጥያቄ ይላኩ',
    sent: 'እናመሰግናለን፤ መልዕክትዎን ተቀብለናል።', footer: 'ለዕለት ተዕለት ኑሮ የተዘጋጀ።',
    saved: 'ተቀምጧል', remove: 'አስወግድ', quantity: 'ብዛት', category: 'ምድብ',
    admin: 'የሱቅ አስተዳዳሪ', signIn: 'ይግቡ', token: 'የአስተዳዳሪ ቁልፍ',
    dashboard: 'አጠቃላይ', products: 'ምርቶች', orders: 'ትዕዛዞች', revenue: 'ገቢ',
    pending: 'በመጠባበቅ ላይ', manageProducts: 'ምርቶችን ያስተዳድሩ', addProduct: 'ምርት ጨምር',
    editProduct: 'ምርት አስተካክል', nameEn: 'የምርት ስም (እንግሊዝኛ)', nameAm: 'የምርት ስም (አማርኛ)',
    descriptionEn: 'መግለጫ (እንግሊዝኛ)', descriptionAm: 'መግለጫ (አማርኛ)',
    price: 'ዋጋ (ብር)', stock: 'የክምችት ብዛት', saveProduct: 'ምርት አስቀምጥ',
    uploadHint: 'ፎቶዎችን ወደዚህ ይጣሉ ወይም ለመጫን ይጫኑ (እስከ 10)', status: 'ሁኔታ አዘምን',
    customer: 'ደንበኛ', total: 'ጠቅላላ', signOut: 'ውጣ', adminLoginError: 'የአስተዳዳሪ ቁልፉ አልተቀበለም',
    openMenu: 'ሜኑ ክፈት', favorites: 'የተወደዱ', language: 'ቋንቋ',
    home: 'ሆም', categories: 'ካታጎሪ', menu: 'ሜኑ', profile: 'ፕሮፋይል',
    settings: 'ሴቲንግ', notifications: 'ማሳወቂያዎች', markAllRead: 'ሁሉንም እንደተነበቡ ምልክት አድርግ',
    allCaughtUp: 'ሁሉንም አይተዋል', noActivity: 'የትዕዛዝ ዝማኔዎች እዚህ ይታያሉ።',
    storeNotice: 'የሱቅ ማስታወቂያ', newArrivals: 'አዳዲስ ምርቶችና ቅናሾች',
    newArrivalsBody: 'አዳዲስ ምርቶችንና ያሉ ቅናሾችን ይመልከቱ።',
    orderPlacedNotice: 'ትዕዛዝዎ ደርሶናል', orderStatusNotice: 'የትዕዛዝ ሁኔታ ተዘምኗል',
    orderCount: 'ትዕዛዞች', savedItems: 'የተቀመጡ ምርቶች', bagSummary: 'በቦርሳ ውስጥ',
    guestName: 'ወደ ሂክማ እንኳን ደህና መጡ', profileDetails: 'የግዢ አጠቃላይ እይታ',
    notificationSettings: 'ማሳወቂያዎችና ማስጠንቀቂያዎች', enableNotifications: 'የትዕዛዝና የሱቅ ማሳወቂያዎችን አሳይ',
    clearReadNotifications: 'የተነበቡ ማሳወቂያዎችን አጽዳ', appearance: 'ገጽታ',
    lightMode: 'ብርሃን ገጽታ', darkMode: 'ጨለማ ገጽታ', storePreferences: 'የግዢና የማሳያ ቅንብሮች',
    clearShoppingData: 'ቦርሳና የአሰሳ ታሪክ አጽዳ', confirmClearStore: 'ቦርሳዎን፣ የታዩ ምርቶችንና የፍለጋ ታሪክን ማጽዳት ይፈልጋሉ?',
    shoppingDataCleared: 'ቦርሳና የአሰሳ ታሪክ ተጽድቷል።', recentViewed: 'በቅርቡ የታዩ',
    recentSearches: 'የቅርብ ፍለጋዎች', languageAmharic: 'አማርኛ', languageEnglish: 'English',
    openSettings: 'ቅንብሮችን ክፈት', adminLink: 'የሱቅ አስተዳዳሪ', notificationCount: 'ያልተነበቡ ማሳወቂያዎች',
    unread: 'ያልተነበቡ', chooseCategory: 'ምድብ ይምረጡ', categoryAll: 'ሁሉም ምርቶች',
    supportFaq: 'ድጋፍና ጥያቄዎች', accountInfo: 'የቴሌግራም መገለጫ',
    storeNavigation: 'የሱቅ አሰሳ', dismiss: 'ዝጋ', noCategories: 'ምድቦች እዚህ ይታያሉ።',
    footerShop: 'ይመልከቱ', footerHelp: 'እገዛና ድጋፍ', footerPreferences: 'ቅንብሮች',
    addToWishlist: 'ወደ የተወደዱ ጨምር', removeFromWishlist: 'ከተወደዱ አስወግድ',
    primaryNavigation: 'ዋና አሰሳ', menuAction: 'ሜኑ',
  },
}

const formatPrice = (value) => `${Number(value || 0).toLocaleString()} ETB`
const savedValue = (key, fallback) => {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback }
}
const savedList = (key) => {
  const value = savedValue(key, [])
  return Array.isArray(value) ? value : []
}

function App({ telegramUser }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('hikma-language') || 'en')
  const [dark, setDark] = useState(() => {
    const savedTheme = localStorage.getItem('hikma-theme')
    return savedTheme ? savedTheme === 'dark' : window.Telegram?.WebApp?.colorScheme === 'dark'
  })
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [supportUsername, setSupportUsername] = useState('')
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('all')
  const [sort, setSort] = useState('newest')
  const [inStock, setInStock] = useState(true)
  const [showFavorites, setShowFavorites] = useState(false)
  const [cart, setCart] = useState(() => savedList('hikma-cart'))
  const [favorites, setFavorites] = useState(() => savedList('hikma-favorites'))
  const [selected, setSelected] = useState(null)
  const [drawer, setDrawer] = useState(false)
  const [checkout, setCheckout] = useState(false)
  const [trackingOpen, setTrackingOpen] = useState(false)
  const [supportOpen, setSupportOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [panel, setPanel] = useState('')
  const [mobileTab, setMobileTab] = useState('home')
  const [notificationOpen, setNotificationOpen] = useState(false)
  const [notifications, setNotifications] = useState(() => savedList('hikma-notifications'))
  const [notificationsEnabled, setNotificationsEnabled] = useState(() => savedValue('hikma-notifications-enabled', true))
  const [localOrders, setLocalOrders] = useState(() => savedList('hikma-local-orders'))
  const [recentlyViewed, setRecentlyViewed] = useState(() => savedList('hikma-recently-viewed'))
  const [searchHistory, setSearchHistory] = useState(() => savedList('hikma-search-history'))
  const notificationRef = useRef(null)
  const searchInputRef = useRef(null)
  const t = words[language]
  const am = language === 'am'
  const unreadCount = notificationsEnabled ? notifications.filter((item) => !item.read).length : 0
  const displayedProducts = showFavorites
    ? products.filter((product) => favorites.includes(product.id))
    : products

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('hikma-theme', dark ? 'dark' : 'light')
  }, [dark])
  useEffect(() => { localStorage.setItem('hikma-language', language) }, [language])
  useEffect(() => { localStorage.setItem('hikma-cart', JSON.stringify(cart)) }, [cart])
  useEffect(() => { localStorage.setItem('hikma-favorites', JSON.stringify(favorites)) }, [favorites])
  useEffect(() => { localStorage.setItem('hikma-notifications', JSON.stringify(notifications)) }, [notifications])
  useEffect(() => { localStorage.setItem('hikma-notifications-enabled', JSON.stringify(notificationsEnabled)) }, [notificationsEnabled])
  useEffect(() => { localStorage.setItem('hikma-local-orders', JSON.stringify(localOrders)) }, [localOrders])
  useEffect(() => { localStorage.setItem('hikma-recently-viewed', JSON.stringify(recentlyViewed)) }, [recentlyViewed])
  useEffect(() => { localStorage.setItem('hikma-search-history', JSON.stringify(searchHistory)) }, [searchHistory])
  useEffect(() => {
    if (!notificationOpen) return undefined
    const closeOnOutsideClick = (event) => {
      if (!notificationRef.current?.contains(event.target)) setNotificationOpen(false)
    }
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') setNotificationOpen(false)
    }
    const closeOnMobileResize = () => {
      if (window.innerWidth < 768) setNotificationOpen(false)
    }
    document.addEventListener('pointerdown', closeOnOutsideClick)
    window.addEventListener('keydown', closeOnEscape)
    window.addEventListener('resize', closeOnMobileResize)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsideClick)
      window.removeEventListener('keydown', closeOnEscape)
      window.removeEventListener('resize', closeOnMobileResize)
    }
  }, [notificationOpen])
  useEffect(() => {
    const params = new URLSearchParams()
    if (query.trim()) params.set('q', query.trim())
    if (category !== 'all') params.set('category', category)
    params.set('sort', sort)
    params.set('in_stock', String(inStock))
    api(`/api/products?${params}`).then(setProducts).catch((error) => setNotice(error.message))
    api('/api/categories').then(setCategories).catch(() => setCategories([]))
  }, [query, category, sort, inStock])
  useEffect(() => {
    api('/api/config').then((settings) => setSupportUsername(settings.support_username || '')).catch(() => {})
  }, [])

  const subtotal = useMemo(() => cart.reduce(
    (sum, line) => sum + Number(line.product.price) * line.quantity, 0,
  ), [cart])
  const quantity = cart.reduce((sum, line) => sum + line.quantity, 0)
  const addToCart = (product, amount = 1) => {
    const line = cart.find((item) => item.product.id === product.id)
    const stock = Number(product.stock_quantity || 0)
    if (line && line.quantity + amount > stock) {
      setNotice(am ? 'ያለው ክምችት ይህን ብዛት አይፈቅድም።' : 'That quantity exceeds available stock.')
      window.setTimeout(() => setNotice(''), 2200)
      return
    }
    if (!line && amount > stock) return
    setCart((current) => line
      ? current.map((item) => item.product.id === product.id ? { ...item, quantity: item.quantity + amount } : item)
      : [...current, { product, quantity: amount }])
    setNotice(am ? 'ወደ ቦርሳ ተጨምሯል' : 'Added to your bag')
    window.setTimeout(() => setNotice(''), 2200)
  }
  const changeQuantity = (id, amount) => setCart((current) => current
    .map((item) => item.product.id === id
      ? { ...item, quantity: Math.max(0, Math.min(Number(item.product.stock_quantity || 0), item.quantity + amount)) }
      : item)
    .filter((item) => item.quantity > 0))
  const toggleFavorite = (id) => setFavorites((current) => (
    current.includes(id) ? current.filter((value) => value !== id) : [...current, id]
  ))
  const openProduct = (product) => {
    setRecentlyViewed((current) => [product.id, ...current.filter((id) => id !== product.id)].slice(0, 20))
    setSelected(product)
  }
  const openPanel = (name) => {
    setNotificationOpen(false)
    setPanel(name)
    setMobileTab(name === 'categories' ? 'categories' : name === 'profile' ? 'profile' : name === 'menu' ? 'menu' : mobileTab)
  }
  const closePanel = () => setPanel('')
  const goHome = () => {
    setPanel('')
    setShowFavorites(false)
    setCategory('all')
    setMobileTab('home')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const goCategories = () => openPanel('categories')
  const chooseCategory = (value) => {
    setCategory(value)
    setShowFavorites(false)
    setPanel('')
    setMobileTab('home')
    window.setTimeout(() => document.getElementById('collection')?.scrollIntoView({ behavior: 'smooth' }), 0)
  }
  const goFavorites = () => {
    setPanel('')
    setShowFavorites(true)
    setCategory('all')
    setMobileTab('home')
    window.setTimeout(() => document.getElementById('collection')?.scrollIntoView({ behavior: 'smooth' }), 0)
  }
  const goHelp = () => {
    setPanel('')
    setMobileTab('menu')
    window.setTimeout(() => document.getElementById('help')?.scrollIntoView({ behavior: 'smooth' }), 0)
  }
  const recordSearch = (value) => {
    const cleaned = value.trim()
    if (!cleaned) return
    setSearchHistory((current) => [cleaned, ...current.filter((item) => item.toLowerCase() !== cleaned.toLowerCase())].slice(0, 10))
  }
  const addNotification = (item) => {
    if (notificationsEnabled) setNotifications((current) => [item, ...current].slice(0, 40))
  }
  const recordOrder = (order) => {
    const orderNumber = order.order_number
    const status = order.status || 'Pending'
    setLocalOrders((current) => [{ order_number: orderNumber, status }, ...current.filter((item) => item.order_number !== orderNumber)].slice(0, 50))
    addNotification({ id: `order-${orderNumber}`, type: 'order', orderNumber, status, read: false, createdAt: Date.now() })
  }
  const recordTrackedOrder = (order) => {
    const previous = localOrders.find((item) => item.order_number === order.order_number)
    setLocalOrders((current) => [
      { order_number: order.order_number, status: order.status },
      ...current.filter((item) => item.order_number !== order.order_number),
    ].slice(0, 50))
    if (previous && previous.status !== order.status) {
      addNotification({
        id: `status-${order.order_number}-${Date.now()}`,
        type: 'status',
        orderNumber: order.order_number,
        status: order.status,
        read: false,
        createdAt: Date.now(),
      })
    }
  }
  const clearShoppingData = () => {
    if (!window.confirm(t.confirmClearStore)) return
    setCart([])
    setRecentlyViewed([])
    setSearchHistory([])
    setQuery('')
    setShowFavorites(false)
    setNotice(t.shoppingDataCleared)
    window.setTimeout(() => setNotice(''), 3000)
  }

  if (window.location.pathname === '/admin') {
    return <AdminPage t={t} am={am} />
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 transition-colors dark:bg-brand-navy dark:text-slate-100">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-slate-50/90 backdrop-blur-xl dark:border-slate-700 dark:bg-brand-navy/90">
        <div className="mx-auto flex h-[72px] max-w-[1440px] items-center gap-2 px-3 sm:h-20 sm:gap-3 sm:px-7 lg:gap-4 lg:px-12">
          <a href="/" className="flex shrink-0 items-center" aria-label="Hikma home">
            <img src="/hikma-logo.png" alt="Hikma Online Shopping — Shop Smart, Buy Easy, Save More" width="64" height="64" className="size-12 bg-white object-contain sm:size-16" />
          </a>
          <label className="hidden h-11 min-w-0 max-w-[360px] flex-1 items-center gap-2.5 rounded-full border border-slate-200 bg-white px-4 transition focus-within:border-brand-blue focus-within:ring-2 focus-within:ring-brand-blue/20 dark:border-slate-700 dark:bg-slate-900 lg:flex">
            <Search size={16} className="shrink-0 text-slate-500" />
            <input ref={searchInputRef} value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && recordSearch(query)} placeholder={t.search} className="w-full min-w-0 bg-transparent text-sm outline-none placeholder:text-slate-400" />
          </label>
          <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-2">
            <button onClick={() => setLanguage(am ? 'en' : 'am')} className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white text-brand-blue shadow-sm transition hover:border-brand-blue/50 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:text-blue-300 dark:hover:bg-slate-700" aria-label={t.language}>
              <Languages size={18} aria-hidden="true" />
            </button>
            <button onClick={() => setDark(!dark)} className="grid size-10 place-items-center rounded-xl border border-slate-200 bg-white transition hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700" aria-label={dark ? t.lightMode : t.darkMode}>
              {dark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
            </button>
            <div className="relative hidden lg:block" ref={notificationRef}>
              <button onClick={() => setNotificationOpen((current) => !current)} className="relative grid size-10 place-items-center rounded-xl border border-slate-200 bg-white transition hover:border-brand-blue/40 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700" aria-label={unreadCount > 0 ? `${t.notifications} (${unreadCount})` : t.notifications} aria-expanded={notificationOpen} aria-haspopup="dialog">
                <Bell size={18} aria-hidden="true" />
                {unreadCount > 0 && <span className="absolute -right-1 -top-1 grid min-h-4 min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[9px] font-bold text-white ring-2 ring-white dark:ring-slate-800" aria-hidden="true">{unreadCount}</span>}
              </button>
              {notificationOpen && <NotificationsPopover notifications={notifications} products={products} t={t} onBrowse={() => { setNotificationOpen(false); document.getElementById('collection')?.scrollIntoView({ behavior: 'smooth' }) }} onMarkAllRead={() => setNotifications((current) => current.map((item) => ({ ...item, read: true })))} />}
            </div>
            <button onClick={() => setDrawer(true)} className="relative grid size-10 shrink-0 place-items-center rounded-xl bg-brand-blue text-white shadow-sm transition hover:bg-brand-blue-hover" aria-label={`${t.bag} (${quantity})`}>
              <ShoppingCart size={19} aria-hidden="true" />
              <span className="absolute -right-1 -top-1 grid min-h-4 min-w-4 place-items-center rounded-full bg-brand-orange px-1 text-[9px] font-bold leading-none text-slate-950" aria-hidden="true">{quantity}</span>
            </button>
            <button onClick={() => setShowFavorites(!showFavorites)} className={`relative hidden size-10 place-items-center rounded-xl border border-slate-200 bg-white transition hover:border-brand-blue/40 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 xl:grid ${showFavorites ? 'text-brand-blue-active' : ''}`} aria-label={t.favorites}>
              <Heart size={18} fill={showFavorites ? 'currentColor' : 'none'} aria-hidden="true" />
              {favorites.length > 0 && <span className="absolute -right-1 -top-1 grid min-h-4 min-w-4 place-items-center rounded-full bg-brand-orange px-1 text-[9px] font-bold text-slate-950">{favorites.length}</span>}
            </button>
            <button onClick={() => setTrackingOpen(true)} className="hidden size-10 place-items-center rounded-xl border border-slate-200 bg-white transition hover:border-brand-blue/40 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 xl:grid" aria-label={t.tracking}>
              <PackageSearch size={18} aria-hidden="true" />
            </button>
            <nav aria-label={t.primaryNavigation} className="hidden shrink-0 items-center gap-0.5 md:flex">
              <button type="button" onClick={goHome} aria-label={t.home} className="grid size-10 shrink-0 place-items-center rounded-lg text-slate-700 transition hover:bg-blue-50 hover:text-brand-blue dark:text-slate-200 dark:hover:bg-slate-800 dark:hover:text-white">
                <House size={18} aria-hidden="true" />
              </button>
              <button type="button" onClick={goCategories} aria-label={t.categories} aria-expanded={panel === 'categories'} className={`grid size-10 shrink-0 place-items-center rounded-lg transition hover:bg-blue-50 hover:text-brand-blue dark:hover:bg-slate-800 dark:hover:text-white ${panel === 'categories' ? 'text-brand-blue' : 'text-slate-700 dark:text-slate-200'}`}>
                <LayoutGrid size={18} aria-hidden="true" />
              </button>
              <button type="button" onClick={() => openPanel('profile')} aria-label={t.profile} aria-expanded={panel === 'profile'} className={`grid size-10 shrink-0 place-items-center rounded-lg transition hover:bg-blue-50 hover:text-brand-blue dark:hover:bg-slate-800 dark:hover:text-white ${panel === 'profile' ? 'text-brand-blue' : 'text-slate-700 dark:text-slate-200'}`}>
                <UserRound size={18} aria-hidden="true" />
              </button>
              <button type="button" onClick={() => openPanel('menu')} aria-label={t.menu} aria-expanded={panel === 'menu'} className={`inline-flex h-10 shrink-0 items-center gap-2 whitespace-nowrap rounded-full border border-brand-blue/40 bg-white px-3 text-xs font-bold tracking-wide text-brand-blue shadow-sm transition hover:border-brand-blue hover:bg-blue-50 dark:border-slate-600 dark:bg-slate-800 dark:text-blue-300 dark:hover:border-blue-400 dark:hover:bg-slate-700 ${panel === 'menu' ? 'ring-2 ring-brand-blue/20' : ''}`}>
                <Menu size={17} aria-hidden="true" /><span>{t.menuAction}</span>
              </button>
            </nav>
          </div>
        </div>
      </header>

      <main className="pb-24 md:pb-8">
        <section className="mx-auto max-w-[1440px] px-4 pt-5 sm:px-7 sm:pt-8 lg:px-12">
          <div className="hero-grid relative min-h-[430px] overflow-hidden rounded-[26px] bg-brand-blue sm:min-h-[500px] sm:rounded-[34px] lg:min-h-[550px]">
            <div className="relative z-10 flex min-h-[430px] max-w-[690px] flex-col items-start justify-center px-7 py-12 text-white sm:min-h-[500px] sm:px-14 lg:min-h-[550px] lg:px-[74px]">
              <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3.5 py-2 text-[11px] uppercase tracking-[.15em] backdrop-blur">{t.heroEyebrow}</span>
              <h1 className="max-w-[620px] text-5xl font-medium leading-[1.07] tracking-[-.055em] sm:text-6xl lg:text-[76px]">{t.heroTitle}</h1>
              <p className="mt-5 max-w-[420px] text-sm leading-7 text-white/75 sm:text-base">{t.heroBody}</p>
              <a href="#collection" className="mt-8 inline-flex items-center gap-3 rounded-full bg-brand-blue px-6 py-3.5 text-sm font-semibold text-white transition hover:-translate-y-0.5 hover:bg-brand-blue-hover">
                {t.explore}<ArrowRight size={16} />
              </a>
            </div>
            <div className="absolute bottom-7 right-7 hidden rounded-2xl border border-white/20 bg-white/10 px-4 py-3 text-xs text-white/80 backdrop-blur sm:block">
              <span className="block text-white">{t.curated}</span><span className="mt-1 block">Hikma / 2026</span>
            </div>
          </div>
        </section>

        <section id="collection" className="mx-auto max-w-[1440px] px-4 pb-20 pt-[72px] sm:px-7 lg:px-12 lg:pt-24">
          <div className="mb-8 flex flex-col justify-between gap-5 md:flex-row md:items-end">
            <div>
              <p className="mb-3 text-xs font-semibold uppercase tracking-[.16em] text-brand-blue-active">{t.curated}</p>
              <h2 className="text-3xl font-medium tracking-[-.04em] sm:text-[40px]">{t.all}</h2>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <label className="flex h-11 items-center gap-2.5 rounded-full border border-slate-200 bg-white px-4 transition focus-within:border-brand-blue focus-within:ring-2 focus-within:ring-brand-blue/20 dark:border-slate-700 dark:bg-slate-900 lg:hidden">
                <Search size={16} className="text-slate-500" />
                <input value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && recordSearch(query)} placeholder={t.search} className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400 sm:w-44" />
              </label>
              <div className="flex gap-2">
                <label className="relative flex h-11 items-center gap-2 rounded-full border border-slate-200 bg-white px-4 text-sm dark:border-slate-700 dark:bg-slate-900">
                  <ArrowDownWideNarrow size={15} className="text-slate-500" />
                  <select value={sort} onChange={(event) => setSort(event.target.value)} className="appearance-none bg-transparent pr-4 outline-none">
                    <option value="newest">{t.newest}</option><option value="price_asc">{t.low}</option><option value="price_desc">{t.high}</option>
                  </select><ChevronDown size={13} className="absolute right-3 pointer-events-none" />
                </label>
                <button onClick={() => setInStock(!inStock)} className={`flex h-11 items-center gap-2 rounded-full border px-4 text-sm transition ${inStock ? 'border-brand-blue bg-brand-blue text-white' : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'}`}>
                  <SlidersHorizontal size={15} /> <span className="hidden sm:inline">{t.inStock}</span>
                </button>
              </div>
            </div>
          </div>

          <div className="soft-scrollbar mb-7 flex gap-2 overflow-x-auto pb-2">
            {[['all', t.all], ...categories.map((name) => [name, am ? categoryLabel(name, true) : name])].map(([value, label]) => (
              <button key={value} onClick={() => setCategory(value)} className={`shrink-0 rounded-full px-4 py-2.5 text-xs font-medium transition ${category === value ? 'bg-brand-blue text-white' : 'border border-slate-200 bg-white text-slate-600 hover:border-brand-blue/40 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300'}`}>{label}</button>
            ))}
          </div>

          {displayedProducts.length === 0 ? (
            <div className="grid min-h-64 place-items-center rounded-3xl border border-dashed border-slate-200 text-center dark:border-slate-700">
              <div><div className="mx-auto mb-4 grid size-12 place-items-center rounded-full bg-blue-50 text-brand-blue-active dark:bg-slate-800"><Search size={19} /></div><h3 className="text-lg font-medium">{t.noProducts}</h3><p className="mt-2 text-sm text-slate-500">{notice || t.noProductsBody}</p></div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-x-3 gap-y-7 sm:grid-cols-3 sm:gap-x-5 sm:gap-y-9 lg:grid-cols-4 lg:gap-x-6">
              {displayedProducts.map((product) => (
                <ProductCard key={product.id} product={product} am={am} t={t} favorite={favorites.includes(product.id)} onFavorite={() => toggleFavorite(product.id)} onClick={() => openProduct(product)} onAdd={() => addToCart(product)} />
              ))}
            </div>
          )}
        </section>

        <section id="promise" className="mx-auto max-w-[1440px] px-4 pb-16 sm:px-7 lg:px-12">
          <div className="rounded-[28px] bg-blue-50 px-7 py-12 text-center dark:bg-slate-900 sm:py-16">
            <p className="text-xs font-semibold uppercase tracking-[.16em] text-brand-blue-active">HIKMA / OUR PROMISE</p>
            <h2 className="mx-auto mt-4 max-w-[680px] text-3xl font-medium leading-tight tracking-[-.045em] sm:text-5xl">{t.promiseTitle}</h2>
            <p className="mx-auto mt-4 max-w-[560px] text-sm leading-7 text-slate-600 dark:text-slate-300">{t.promiseBody}</p>
          </div>
        </section>

        <HelpSection t={t} supportUrl={supportUsername ? `https://t.me/${supportUsername}` : 'https://t.me/'} onTrack={() => setTrackingOpen(true)} onSupport={() => setSupportOpen(true)} />
      </main>

      <footer className="border-t border-slate-200 pb-24 dark:border-slate-700 md:pb-0">
        <div className="mx-auto max-w-[1440px] px-4 py-10 sm:px-7 sm:py-12 lg:px-12">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr] lg:gap-12">
            <div className="max-w-sm">
              <a href="/" aria-label="Hikma home" className="inline-flex items-center">
                <img src="/hikma-logo.png" alt="Hikma Online Shopping — Shop Smart, Buy Easy, Save More" width="64" height="64" className="size-16 bg-white object-contain" />
              </a>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{t.promiseBody}</p>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">{t.footerShop}</h2>
              <div className="mt-4 flex flex-col items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                <a href="#collection" className="hover:text-brand-blue">{t.shop}</a>
                <button onClick={goCategories} className="hover:text-brand-blue">{t.categories}</button>
                <a href="#promise" className="hover:text-brand-blue">{t.story}</a>
              </div>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">{t.footerHelp}</h2>
              <div className="mt-4 flex flex-col items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                <a href="#help" className="hover:text-brand-blue">{t.help}</a>
                <button onClick={() => setTrackingOpen(true)} className="hover:text-brand-blue">{t.tracking}</button>
                <button onClick={() => setSupportOpen(true)} className="hover:text-brand-blue">{t.support}</button>
                <a href={supportUsername ? `https://t.me/${supportUsername}` : 'https://t.me/'} target="_blank" rel="noreferrer" className="hover:text-brand-blue">Telegram ↗</a>
              </div>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-white">{t.footerPreferences}</h2>
              <div className="mt-4 flex flex-col items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                <button onClick={() => openPanel('settings')} className="hover:text-brand-blue">{t.settings}</button>
                <button onClick={() => setLanguage(am ? 'en' : 'am')} className="hover:text-brand-blue">{t.language}: {am ? t.languageEnglish : t.languageAmharic}</button>
                <button onClick={() => setDark((value) => !value)} className="hover:text-brand-blue">{dark ? t.lightMode : t.darkMode}</button>
              </div>
            </div>
          </div>
          <div className="mt-8 border-t border-slate-200 pt-5 text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400">
            {t.footer} © {new Date().getFullYear()} Hikma Online Shopping.
          </div>
        </div>
      </footer>

      <MobileBottomNavigation active={mobileTab} t={t} onHome={goHome} onCategories={goCategories} onMenu={() => openPanel('menu')} onProfile={() => openPanel('profile')} />
      {panel === 'menu' && <MenuPanel t={t} onClose={closePanel} onHome={goHome} onCategories={goCategories} onTrack={() => { closePanel(); setTrackingOpen(true) }} onFavorites={goFavorites} onPromise={() => { closePanel(); window.setTimeout(() => document.getElementById('promise')?.scrollIntoView({ behavior: 'smooth' }), 0) }} onHelp={goHelp} onSupport={() => { closePanel(); setSupportOpen(true) }} onSettings={() => openPanel('settings')} />}
      {panel === 'categories' && <CategoriesPanel categories={categories} category={category} am={am} t={t} onClose={closePanel} onChoose={chooseCategory} />}
      {panel === 'profile' && <ProfilePanel telegramUser={telegramUser} localOrders={localOrders} favorites={favorites} quantity={quantity} t={t} onClose={closePanel} onTrack={() => { closePanel(); setTrackingOpen(true) }} onFavorites={goFavorites} onSettings={() => openPanel('settings')} />}
      {panel === 'settings' && <SettingsPanel t={t} am={am} dark={dark} quantity={quantity} notificationsEnabled={notificationsEnabled} notifications={notifications} recentlyViewed={recentlyViewed} searchHistory={searchHistory} onClose={closePanel} onLanguage={setLanguage} onTheme={setDark} onToggleNotifications={() => setNotificationsEnabled((current) => !current)} onClearRead={() => setNotifications((current) => current.filter((item) => !item.read))} onClearShoppingData={clearShoppingData} onTrack={() => { closePanel(); setTrackingOpen(true) }} onHelp={goHelp} onSupport={() => { closePanel(); setSupportOpen(true) }} />}
      {notice && products.length > 0 && <div role="status" className="fixed bottom-5 left-1/2 z-[80] -translate-x-1/2 rounded-full bg-brand-blue px-5 py-3 text-sm text-white shadow-xl">{notice}</div>}
      {selected && <ProductModal product={selected} am={am} t={t} favorite={favorites.includes(selected.id)} onFavorite={() => toggleFavorite(selected.id)} onClose={() => setSelected(null)} onAdd={(amount) => { addToCart(selected, amount); setDrawer(true) }} />}
      {drawer && <CartDrawer cart={cart} t={t} am={am} initialName={[telegramUser?.first_name, telegramUser?.last_name].filter(Boolean).join(' ')} subtotal={subtotal} checkout={checkout} setCheckout={setCheckout} onChange={changeQuantity} onRemove={(id) => setCart((current) => current.filter((item) => item.product.id !== id))} onClose={() => { setDrawer(false); setCheckout(false) }} onOrder={(order) => { recordOrder(order); setCart([]); setCheckout(false); setNotice(`${t.orderSuccess} · ${order.order_number}`); setTimeout(() => setNotice(''), 6000) }} />}
      {trackingOpen && <TrackingModal t={t} onClose={() => setTrackingOpen(false)} onTracked={recordTrackedOrder} />}
      {supportOpen && <SupportModal t={t} supportUrl={supportUsername ? `https://t.me/${supportUsername}` : 'https://t.me/'} onClose={() => setSupportOpen(false)} />}
      {telegramUser?.first_name && <span className="sr-only">{telegramUser.first_name}</span>}
    </div>
  )
}

function categoryLabel(category, am) {
  const labels = { men: 'ወንዶች', women: 'ሴቶች', accessories: 'መለዋወጫዎች', footwear: 'ጫማዎች', home: 'የቤት እቃዎች' }
  return am ? (labels[category.toLowerCase()] || category) : category
}

function ProductCard({ product, am, t, favorite, onFavorite, onClick, onAdd }) {
  const name = product[am ? 'name_am' : 'name_en'] || product.name_en || product.name_am
  const image = product.images?.[0]
  const discount = Number(product.discount_percent)
  const hasDiscount = discount > 0 || product.is_on_sale
  return (
    <article className="group min-w-0">
      <div className="relative aspect-[.82] overflow-hidden rounded-2xl bg-slate-100 dark:bg-slate-800 sm:rounded-[22px]">
        <button onClick={onClick} className="h-full w-full text-left" aria-label={`${t.details}: ${name}`}>
          {image ? <img src={image} alt={name} loading="lazy" className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.035]" /> : <div className="grid h-full place-items-center text-slate-400"><ShoppingBag size={34} strokeWidth={1.2} /></div>}
        </button>
        <span className={`absolute left-3 top-3 rounded-full px-3 py-1.5 text-[10px] font-semibold backdrop-blur ${Number(product.stock_quantity) > 0 ? 'bg-brand-orange text-slate-950' : 'bg-slate-900/85 text-white'}`}>
          {Number(product.stock_quantity) > 0 ? `${product.stock_quantity} ${am ? 'ቀርቷል' : 'left'}` : t.soldOut}
        </span>
        {hasDiscount && <span className="absolute left-3 top-12 rounded-full bg-brand-amber px-3 py-1.5 text-[10px] font-semibold text-slate-950">{discount > 0 ? `-${discount}%` : am ? 'ቅናሽ' : 'Sale'}</span>}
      </div>
      <button onClick={onClick} className="mt-3 block w-full text-left">
        <span className="block truncate text-[13px] font-medium sm:text-sm">{name}</span>
        <span className="mt-1.5 flex min-w-0 items-center justify-between gap-2">
          <span className="shrink-0 text-sm font-semibold">{formatPrice(product.price)}</span>
          <span className="max-w-[52%] truncate rounded-full bg-slate-100 px-2 py-1 text-[10px] text-slate-600 dark:bg-slate-800 dark:text-slate-300">{am ? categoryLabel(product.category || '', true) : product.category}</span>
        </span>
      </button>
      <div className="mt-2.5 flex items-center gap-2">
        <button onClick={onFavorite} className="grid size-9 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-brand-blue transition hover:border-brand-blue/40 hover:bg-blue-50 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800" aria-label={favorite ? t.removeFromWishlist : t.addToWishlist} title={favorite ? t.removeFromWishlist : t.addToWishlist}>
          <Heart size={16} fill={favorite ? 'var(--color-brand-blue)' : 'none'} />
        </button>
        <button disabled={!Number(product.stock_quantity)} onClick={onAdd} className="inline-flex min-w-0 flex-1 items-center justify-center gap-1.5 rounded-xl bg-brand-blue px-2 py-2.5 text-[11px] font-semibold text-white transition hover:bg-brand-blue-hover disabled:cursor-not-allowed disabled:opacity-50">
          <Plus size={15} className="shrink-0" /><span className="truncate">{Number(product.stock_quantity) ? t.add : t.soldOut}</span>
        </button>
      </div>
    </article>
  )
}

function ProductModal({ product, am, t, favorite, onFavorite, onClose, onAdd }) {
  const [photo, setPhoto] = useState(0)
  const [count, setCount] = useState(1)
  const [touchStart, setTouchStart] = useState(null)
  const images = product.images?.length ? product.images : []
  const name = product[am ? 'name_am' : 'name_en'] || product.name_en || product.name_am
  const description = product[am ? 'description_am' : 'description_en'] || product.description_en || product.description_am || ''
  const next = (offset) => setPhoto((current) => (current + offset + images.length) % images.length)
  return (
    <div className="modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-5" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <div className="relative grid h-full w-full grid-cols-1 overflow-y-auto bg-white dark:bg-slate-900 sm:h-auto sm:max-h-[90vh] sm:max-w-[920px] sm:grid-cols-2 sm:rounded-[28px]">
        <button onClick={onClose} className="absolute right-4 top-4 z-10 grid size-10 place-items-center rounded-full bg-white/90 shadow-sm dark:bg-slate-900" aria-label="Close"><X size={18} /></button>
        <div
          className="relative min-h-[44vh] bg-slate-100 dark:bg-slate-800 sm:min-h-[560px]"
          onTouchStart={(event) => setTouchStart(event.touches[0].clientX)}
          onTouchEnd={(event) => {
            if (touchStart === null || images.length < 2) return
            const distance = event.changedTouches[0].clientX - touchStart
            if (Math.abs(distance) > 40) next(distance > 0 ? -1 : 1)
            setTouchStart(null)
          }}
        >
          {images[photo] ? <img src={images[photo]} alt={name} className="h-full min-h-[44vh] w-full object-cover sm:min-h-[560px]" /> : <div className="grid h-full min-h-[44vh] place-items-center text-slate-400"><ShoppingBag size={42} /></div>}
          {images.length > 1 && <><button onClick={() => next(-1)} className="absolute left-4 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-white/90"><ChevronLeft size={20} /></button><button onClick={() => next(1)} className="absolute right-4 top-1/2 grid size-10 -translate-y-1/2 place-items-center rounded-full bg-white/90"><ChevronRight size={20} /></button></>}
          {images.length > 1 && <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-2">{images.map((image, index) => <button key={image} onClick={() => setPhoto(index)} className={`size-2 rounded-full ${index === photo ? 'bg-white' : 'bg-white/45'}`} aria-label={`Photo ${index + 1}`} />)}</div>}
        </div>
        <div className="flex flex-col px-6 py-7 sm:px-10 sm:py-12">
          <p className="text-xs font-semibold uppercase tracking-[.16em] text-brand-blue-active">{am ? categoryLabel(product.category || '', true) : product.category}</p>
          <h2 className="mt-3 text-3xl font-medium leading-tight tracking-[-.04em]">{name}</h2>
          <p className="mt-4 text-lg font-semibold">{formatPrice(product.price)}</p>
          {description && <p className="mt-5 whitespace-pre-line text-sm leading-7 text-slate-600 dark:text-slate-300">{description}</p>}
          <div className="mt-6 flex items-center justify-between border-y border-slate-200 py-4 text-sm dark:border-slate-700">
            <span>{t.quantity}</span><div className="flex items-center gap-4"><button onClick={() => setCount(Math.max(1, count - 1))}><Minus size={16} /></button><span>{count}</span><button onClick={() => setCount(Math.min(Number(product.stock_quantity || 1), count + 1))}><Plus size={16} /></button></div>
          </div>
          <div className="mt-auto flex gap-3 pt-7">
            <button onClick={() => onAdd(count)} disabled={!Number(product.stock_quantity)} className="flex-1 rounded-full bg-brand-blue px-5 py-3.5 text-sm font-semibold text-white transition hover:bg-brand-blue-hover disabled:opacity-50">{Number(product.stock_quantity) ? t.add : t.soldOut}</button>
            <button onClick={onFavorite} className="grid size-12 place-items-center rounded-full border border-slate-200 dark:border-slate-700" aria-label="Toggle wishlist"><Heart size={18} fill={favorite ? 'var(--color-brand-blue)' : 'none'} /></button>
          </div>
        </div>
      </div>
    </div>
  )
}

function CartDrawer({ cart, t, am, initialName, subtotal, checkout, setCheckout, onChange, onRemove, onClose, onOrder }) {
  const [form, setForm] = useState(() => ({ name: initialName || '', phone: '', city: '', address: '', payment_method: 'cod' }))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(null)
  const update = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const order = await api('/api/orders', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          items: cart.map(({ product, quantity }) => ({ product_id: product.id, quantity })),
        }),
      })
      setSuccess(order)
      onOrder(order)
    } catch (problem) {
      setError(problem.message)
    } finally { setBusy(false) }
  }
  return (
    <div className="fixed inset-0 z-50">
      <div className="modal-backdrop absolute inset-0" onClick={onClose} />
      <aside className="drawer-shadow absolute right-0 top-0 flex h-full w-full max-w-[500px] flex-col bg-white dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5 dark:border-slate-700 sm:px-8">
          <div><p className="text-xs uppercase tracking-[.14em] text-slate-500">{checkout ? t.yourDetails : t.bag}</p><h2 className="mt-1 text-xl font-medium">{success ? t.orderSuccess : checkout ? t.checkout : `${t.bag} (${cart.reduce((sum, line) => sum + line.quantity, 0)})`}</h2></div>
          <button onClick={onClose} className="grid size-10 place-items-center rounded-full hover:bg-black/5 dark:hover:bg-white/10" aria-label="Close"><X size={19} /></button>
        </div>
        {success ? (
          <div className="grid flex-1 content-center justify-items-center px-8 text-center">
            <div className="grid size-16 place-items-center rounded-full bg-orange-100 text-brand-blue-active"><Check size={28} /></div>
            <p className="mt-5 text-sm text-slate-500">{t.orderSuccessBody}</p>
            <p className="mt-6 rounded-full bg-slate-100 px-4 py-2 text-sm dark:bg-slate-800">{t.orderNumber}: <strong>{success.order_number}</strong></p>
            <button onClick={onClose} className="mt-7 rounded-full bg-brand-blue px-6 py-3 text-sm font-medium text-white">{t.close}</button>
          </div>
        ) : !checkout ? (
          <>
            <div className="soft-scrollbar flex-1 overflow-y-auto px-6 sm:px-8">
              {cart.length === 0 ? <div className="grid h-full content-center justify-items-center text-center"><div className="grid size-14 place-items-center rounded-full bg-slate-100 text-brand-blue-active dark:bg-slate-800"><ShoppingBag size={22} /></div><h3 className="mt-5 text-lg font-medium">{t.emptyBag}</h3><p className="mt-2 max-w-[250px] text-sm leading-6 text-slate-500">{t.emptyBagBody}</p></div> : cart.map(({ product, quantity }) => (
                <div key={product.id} className="flex gap-4 border-b border-slate-200 py-5 dark:border-slate-700">
                  <img src={product.images?.[0]} alt="" className="size-[92px] rounded-xl bg-slate-100 object-cover dark:bg-slate-800" />
                  <div className="flex min-w-0 flex-1 flex-col justify-between py-1"><div className="flex items-start justify-between gap-3"><p className="truncate text-sm font-medium">{product[am ? 'name_am' : 'name_en'] || product.name_en}</p><button onClick={() => onRemove(product.id)} aria-label={t.remove}><Trash2 size={15} className="text-slate-400" /></button></div><div className="flex items-end justify-between"><div className="flex items-center gap-3 rounded-full border border-slate-200 px-2.5 py-1.5 dark:border-slate-700"><button onClick={() => onChange(product.id, -1)}><Minus size={13} /></button><span className="min-w-3 text-center text-xs">{quantity}</span><button onClick={() => onChange(product.id, 1)}><Plus size={13} /></button></div><span className="text-sm font-semibold">{formatPrice(Number(product.price) * quantity)}</span></div></div>
                </div>
              ))}
            </div>
            <div className="border-t border-slate-200 px-6 py-5 dark:border-slate-700 sm:px-8">
              <div className="flex justify-between text-sm"><span>{t.subtotal}</span><strong>{formatPrice(subtotal)}</strong></div>
              <p className="mt-2 text-xs leading-5 text-slate-500">{t.deliveryNote}</p>
              <button disabled={!cart.length} onClick={() => setCheckout(true)} className="mt-5 w-full rounded-full bg-brand-blue py-3.5 text-sm font-semibold text-white transition hover:bg-brand-blue-hover disabled:cursor-not-allowed disabled:opacity-40">{t.checkout}</button>
            </div>
          </>
        ) : (
          <form onSubmit={submit} className="soft-scrollbar flex-1 overflow-y-auto px-6 py-6 sm:px-8">
            <div className="space-y-4">
              <Field label={t.fullName} value={form.name} onChange={update('name')} required />
              <Field label={t.phone} value={form.phone} onChange={update('phone')} type="tel" required />
              <Field label={t.city} value={form.city} onChange={update('city')} required />
              <Field label={t.address} value={form.address} onChange={update('address')} required />
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">{t.payment}
                <select value={form.payment_method} onChange={update('payment_method')} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white">
                  <option value="cod">{t.cash}</option><option value="telebirr">{t.telebirr}</option><option value="cbe">{t.cbe}</option>
                </select>
              </label>
            </div>
            {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300">{error}</p>}
            <div className="mt-7 flex justify-between border-t border-slate-200 pt-5 text-sm dark:border-slate-700"><span>{t.subtotal}</span><strong>{formatPrice(subtotal)}</strong></div>
            <button disabled={busy || cart.length === 0} className="mt-5 w-full rounded-full bg-brand-blue py-3.5 text-sm font-semibold text-white disabled:opacity-50">{busy ? t.placing : t.placeOrder}</button>
            <button type="button" onClick={() => setCheckout(false)} className="mt-3 w-full rounded-full py-3 text-sm text-slate-600">{t.backToBag}</button>
          </form>
        )}
      </aside>
    </div>
  )
}

function Field({ label, value, onChange, type = 'text', required = false, ...props }) {
  return <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">{label}<input type={type} required={required} value={value} onChange={onChange} {...props} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white" /></label>
}

function TrackingModal({ t, onClose, onTracked }) {
  const [orderNumber, setOrderNumber] = useState('')
  const [phone, setPhone] = useState('')
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    if (!orderNumber.trim() && !phone.trim()) {
      setError(t.trackingHelp)
      setBusy(false)
      return
    }
    try {
      const trackedOrder = await api('/api/orders/track', { method: 'POST', body: JSON.stringify({ order_number: orderNumber, phone }) })
      setOrder(trackedOrder)
      onTracked(trackedOrder)
    }
    catch (problem) { setError(problem.message) }
    finally { setBusy(false) }
  }
  return <Modal title={t.trackTitle} onClose={onClose}>
    <p className="mb-5 text-sm text-slate-500">{t.trackingHelp}</p>
    <form onSubmit={submit} className="space-y-4">
      <Field label={t.orderNumber} value={orderNumber} onChange={(event) => setOrderNumber(event.target.value)} />
      <Field label={t.phone} type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} />
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <button disabled={busy} className="w-full rounded-full bg-brand-blue py-3 text-sm font-semibold text-white">{busy ? '…' : t.trackAction}</button>
    </form>
    {order && <div className="mt-5 rounded-2xl bg-slate-100 p-4 dark:bg-slate-800"><p className="text-xs text-slate-500">{t.trackingResult}</p><p className="mt-1 font-semibold">{order.status}</p><p className="mt-2 text-xs">{order.order_number}</p></div>}
  </Modal>
}

function SupportModal({ t, supportUrl, onClose }) {
  const [form, setForm] = useState({ name: '', phone: '', message: '' })
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event) => {
    event.preventDefault(); setError('')
    try {
      await api('/api/support', { method: 'POST', body: JSON.stringify(form) })
      setSent(true)
    } catch (problem) { setError(problem.message) }
  }
  return <Modal title={t.supportTitle} onClose={onClose}>
    {sent ? <p role="status" className="rounded-2xl bg-slate-100 p-5 text-sm dark:bg-slate-800">{t.sent}</p> : <form onSubmit={submit} className="space-y-4">
      <Field label={t.supportName} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
      <Field label={t.phone} type="tel" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} required />
      <label className="block text-xs font-medium text-slate-600 dark:text-slate-300">{t.supportMessage}<textarea required maxLength={2000} value={form.message} onChange={(event) => setForm({ ...form, message: event.target.value })} className="mt-2 min-h-28 w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none transition focus:border-brand-blue focus:ring-2 focus:ring-brand-blue/20 dark:border-slate-700 dark:bg-slate-800" /></label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <button className="w-full rounded-full bg-brand-blue py-3 text-sm font-semibold text-white">{t.send}</button>
    </form>}
    <a className="mt-4 flex items-center justify-center gap-2 text-sm text-brand-blue-active hover:underline" href={supportUrl} target="_blank" rel="noreferrer"><CircleHelp size={15} /> Telegram support</a>
  </Modal>
}

function Modal({ title, children, onClose }) {
  return <div className="modal-backdrop fixed inset-0 z-[60] grid place-items-center p-4" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
    <div className="relative max-h-[92vh] w-full max-w-[440px] overflow-y-auto rounded-[24px] bg-white p-6 dark:bg-slate-900 sm:p-8">
      <button onClick={onClose} className="absolute right-5 top-5 grid size-8 place-items-center rounded-full hover:bg-black/5 dark:hover:bg-white/10"><X size={17} /></button>
      <h2 className="mb-5 pr-8 text-2xl font-medium tracking-tight">{title}</h2>{children}
    </div>
  </div>
}

function HelpSection({ t, supportUrl, onTrack, onSupport }) {
  return <section id="help" className="mx-auto max-w-[1440px] px-4 pb-20 sm:px-7 lg:px-12">
    <div className="grid gap-10 md:grid-cols-[.8fr_1.2fr] md:gap-16">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[.16em] text-brand-blue-active">{t.help}</p>
        <h2 className="mt-3 text-3xl font-medium tracking-[-.04em]">{t.faqs}</h2>
        <div className="mt-6 flex flex-wrap gap-3">
          <button onClick={onTrack} className="rounded-full bg-brand-blue px-5 py-3 text-sm font-medium text-white">{t.tracking}</button>
          <button onClick={onSupport} className="rounded-full border border-slate-200 px-5 py-3 text-sm font-medium dark:border-slate-700">{t.support}</button>
          <a href={supportUrl} target="_blank" rel="noreferrer" className="rounded-full border border-slate-200 px-5 py-3 text-sm font-medium dark:border-slate-700">Telegram ↗</a>
        </div>
      </div>
      <div className="divide-y divide-slate-200 dark:divide-slate-700">
        {[[t.shippingQ, t.shippingA], [t.paymentQ, t.paymentA], [t.returnsQ, t.returnsA]].map(([question, answer]) => <details key={question} className="group py-5 first:pt-0"><summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-sm font-medium">{question}<Plus size={16} className="shrink-0 transition group-open:rotate-45" /></summary><p className="mt-3 max-w-[600px] text-sm leading-6 text-slate-500">{answer}</p></details>)}
      </div>
    </div>
  </section>
}

function MobileBottomNavigation({ active, t, onHome, onCategories, onMenu, onProfile }) {
  const items = [
    { id: 'home', label: t.home, Icon: House, onClick: onHome },
    { id: 'categories', label: t.categories, Icon: LayoutGrid, onClick: onCategories },
    { id: 'profile', label: t.profile, Icon: UserRound, onClick: onProfile },
    { id: 'menu', label: t.menu, Icon: Menu, onClick: onMenu },
  ]
  return <nav aria-label={t.storeNavigation} className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-8px_24px_rgb(15_23_42_/_8%)] backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/95 md:hidden">
    <div className="mx-auto grid min-h-16 max-w-lg grid-cols-4">
      {items.map(({ id, label, Icon, onClick }) => {
        const selected = active === id
        return <button key={id} type="button" onClick={onClick} aria-label={label} aria-current={selected ? 'page' : undefined} className={`flex min-w-0 flex-col items-center justify-center gap-1 px-1 text-[10px] font-medium transition sm:text-xs ${selected ? 'text-brand-blue' : 'text-slate-500 dark:text-slate-300'}`}>
          <span className="relative grid size-8 place-items-center">
            <Icon size={20} strokeWidth={selected ? 2.4 : 1.8} />
            {selected && <span className="absolute -bottom-0.5 size-1 rounded-full bg-brand-orange" />}
          </span>
          <span className="max-w-full truncate">{label}</span>
        </button>
      })}
    </div>
  </nav>
}

function DrawerPanel({ title, subtitle, t, onClose, children }) {
  const titleId = useId()
  const subtitleId = useId()
  useEffect(() => {
    const closeOnEscape = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return <div className="fixed inset-0 z-[70]">
    <button type="button" aria-label={t.dismiss} className="modal-backdrop absolute inset-0" onClick={onClose} />
    <aside role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={subtitle ? subtitleId : undefined} tabIndex={-1} className="absolute inset-x-0 bottom-0 flex max-h-[88vh] flex-col overflow-hidden rounded-t-[28px] bg-white shadow-2xl dark:bg-slate-900 md:inset-y-0 md:left-auto md:right-0 md:h-full md:max-h-full md:w-[440px] md:rounded-l-3xl md:rounded-tr-none">
      <div className="mx-auto mt-3 h-1 w-10 shrink-0 rounded-full bg-slate-300 dark:bg-slate-600 md:hidden" />
      <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-5 dark:border-slate-700 sm:px-7">
        <div className="min-w-0">
          <h2 id={titleId} className="text-xl font-semibold">{title}</h2>
          {subtitle && <p id={subtitleId} className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        </div>
        <button type="button" autoFocus onClick={onClose} className="grid size-9 shrink-0 place-items-center rounded-full text-slate-500 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800" aria-label={t.dismiss}>
          <X size={18} />
        </button>
      </div>
      <div className="soft-scrollbar min-h-0 flex-1 overflow-y-auto px-5 py-5 sm:px-7">{children}</div>
    </aside>
  </div>
}

function PanelAction({ Icon, label, description, onClick }) {
  return <button type="button" onClick={onClick} className="flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-white p-3 text-left transition hover:border-brand-blue/40 hover:bg-blue-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:bg-slate-800">
    <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-blue-50 text-brand-blue dark:bg-slate-800"><Icon size={18} /></span>
    <span className="min-w-0 flex-1">
      <span className="block text-sm font-medium">{label}</span>
      {description && <span className="mt-0.5 block text-xs text-slate-500 dark:text-slate-400">{description}</span>}
    </span>
    <ChevronRight size={16} className="shrink-0 text-slate-400" />
  </button>
}

function MenuPanel({ t, onClose, onHome, onCategories, onTrack, onFavorites, onPromise, onHelp, onSupport, onSettings }) {
  return <DrawerPanel title={t.menu} subtitle={t.supportFaq} t={t} onClose={onClose}>
    <div className="space-y-2.5">
      <PanelAction Icon={House} label={t.home} onClick={onHome} />
      <PanelAction Icon={LayoutGrid} label={t.categories} onClick={onCategories} />
      <PanelAction Icon={ShoppingBag} label={t.tracking} onClick={onTrack} />
      <PanelAction Icon={Heart} label={t.favorites} onClick={onFavorites} />
      <PanelAction Icon={Sparkles} label={t.story} onClick={onPromise} />
      <PanelAction Icon={BookOpen} label={t.faqs} onClick={onHelp} />
      <PanelAction Icon={CircleHelp} label={t.support} onClick={onSupport} />
      <a href="/admin" className="flex items-center gap-3 rounded-2xl border border-slate-200 p-3 transition hover:border-brand-blue/40 hover:bg-blue-50/60 dark:border-slate-700 dark:hover:bg-slate-800">
        <span className="grid size-10 place-items-center rounded-xl bg-blue-50 text-brand-blue dark:bg-slate-800"><Store size={18} /></span>
        <span className="text-sm font-medium">{t.adminLink}</span>
        <ArrowRight size={16} className="ml-auto text-slate-400" />
      </a>
      <PanelAction Icon={Settings} label={t.settings} onClick={onSettings} />
    </div>
  </DrawerPanel>
}

function CategoriesPanel({ categories, category, am, t, onClose, onChoose }) {
  const choices = ['all', ...categories]
  return <DrawerPanel title={t.categories} subtitle={t.chooseCategory} t={t} onClose={onClose}>
    <div className="space-y-2">
      {choices.map((value) => {
        const label = value === 'all' ? t.categoryAll : am ? categoryLabel(value, true) : value
        const selected = category === value
        return <button key={value} type="button" onClick={() => onChoose(value)} aria-current={selected ? 'true' : undefined} className={`flex w-full items-center justify-between rounded-2xl border px-4 py-4 text-left text-sm font-medium transition ${selected ? 'border-brand-blue bg-brand-blue text-white' : 'border-slate-200 bg-white hover:border-brand-blue/40 dark:border-slate-700 dark:bg-slate-900'}`}>
          <span>{label}</span>{selected && <Check size={17} />}
        </button>
      })}
      {categories.length === 0 && <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-800 dark:text-slate-300">{t.noCategories}</p>}
    </div>
  </DrawerPanel>
}

function ProfilePanel({ telegramUser, localOrders, favorites, quantity, t, onClose, onTrack, onFavorites, onSettings }) {
  const name = [telegramUser?.first_name, telegramUser?.last_name].filter(Boolean).join(' ') || t.guestName
  return <DrawerPanel title={t.profile} subtitle={t.profileDetails} t={t} onClose={onClose}>
    <div className="flex items-center gap-4 rounded-2xl bg-blue-50 p-4 dark:bg-slate-800">
      <span className="grid size-14 shrink-0 place-items-center rounded-full bg-white text-brand-blue dark:bg-slate-900"><UserRound size={25} /></span>
      <div className="min-w-0">
        <p className="truncate font-semibold">{name}</p>
        <p className="mt-1 truncate text-sm text-slate-500 dark:text-slate-300">{telegramUser?.username ? `@${telegramUser.username}` : telegramUser?.language_code || (telegramUser ? t.accountInfo : t.profileDetails)}</p>
      </div>
    </div>
    <div className="mt-4 grid grid-cols-3 gap-2">
      {[[t.orderCount, localOrders.length], [t.savedItems, favorites.length], [t.bagSummary, quantity]].map(([label, count]) => <div key={label} className="rounded-2xl border border-slate-200 p-3 text-center dark:border-slate-700">
        <p className="text-lg font-semibold text-brand-blue">{count}</p><p className="mt-1 text-[11px] leading-4 text-slate-500 dark:text-slate-400">{label}</p>
      </div>)}
    </div>
    <div className="mt-5 space-y-2.5">
      <PanelAction Icon={ShoppingBag} label={t.tracking} description={localOrders[0]?.order_number || t.trackTitle} onClick={onTrack} />
      <PanelAction Icon={Heart} label={t.favorites} onClick={onFavorites} />
      <PanelAction Icon={Settings} label={t.settings} onClick={onSettings} />
    </div>
  </DrawerPanel>
}

function SettingsPanel({ t, am, dark, quantity, notificationsEnabled, notifications, recentlyViewed, searchHistory, onClose, onLanguage, onTheme, onToggleNotifications, onClearRead, onClearShoppingData, onTrack, onHelp, onSupport }) {
  const readCount = notifications.filter((item) => item.read).length
  return <DrawerPanel title={t.settings} subtitle={t.storePreferences} t={t} onClose={onClose}>
    <section>
      <h3 className="text-sm font-semibold">{t.language}</h3>
      <div className="mt-2 grid grid-cols-2 gap-2">
        {[['en', t.languageEnglish], ['am', t.languageAmharic]].map(([value, label]) => <button key={value} type="button" onClick={() => onLanguage(value)} aria-pressed={am === (value === 'am')} className={`rounded-xl border px-4 py-3 text-sm font-medium transition ${am === (value === 'am') ? 'border-brand-blue bg-blue-50 text-brand-blue dark:bg-slate-800' : 'border-slate-200 dark:border-slate-700'}`}>{label}</button>)}
      </div>
    </section>
    <section className="mt-6">
      <h3 className="text-sm font-semibold">{t.appearance}</h3>
      <div className="mt-2 grid grid-cols-2 gap-2">
        {[[false, t.lightMode, Sun], [true, t.darkMode, Moon]].map(([value, label, Icon]) => <button key={String(value)} type="button" onClick={() => onTheme(value)} aria-pressed={dark === value} className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-3 text-sm font-medium transition ${dark === value ? 'border-brand-blue bg-blue-50 text-brand-blue dark:bg-slate-800' : 'border-slate-200 dark:border-slate-700'}`}><Icon size={16} />{label}</button>)}
      </div>
    </section>
    <section className="mt-6">
      <h3 className="text-sm font-semibold">{t.notificationSettings}</h3>
      <div className="mt-2 flex items-center justify-between gap-4 rounded-2xl border border-slate-200 p-4 dark:border-slate-700">
        <span className="text-sm">{t.enableNotifications}</span>
        <button type="button" role="switch" aria-checked={notificationsEnabled} aria-label={t.enableNotifications} onClick={onToggleNotifications} className={`relative h-6 w-11 shrink-0 rounded-full transition ${notificationsEnabled ? 'bg-brand-blue' : 'bg-slate-300 dark:bg-slate-600'}`}>
          <span className={`absolute top-1 size-4 rounded-full bg-white transition ${notificationsEnabled ? 'left-6' : 'left-1'}`} />
        </button>
      </div>
      <button type="button" onClick={onClearRead} disabled={!readCount} className="mt-2 flex w-full items-center justify-between rounded-xl px-1 py-2 text-left text-sm text-brand-blue-active disabled:cursor-not-allowed disabled:opacity-40">
        <span>{t.clearReadNotifications}</span><span>{readCount}</span>
      </button>
    </section>
    <section className="mt-6">
      <h3 className="text-sm font-semibold">{t.storePreferences}</h3>
      <div className="mt-2 grid grid-cols-3 gap-2 text-center">
        {[[t.bagSummary, quantity], [t.recentViewed, recentlyViewed.length], [t.recentSearches, searchHistory.length]].map(([label, count]) => <div key={label} className="rounded-xl bg-slate-50 p-3 dark:bg-slate-800">
          <p className="font-semibold">{count}</p><p className="mt-1 text-[10px] leading-4 text-slate-500 dark:text-slate-400">{label}</p>
        </div>)}
      </div>
      <button type="button" onClick={onClearShoppingData} disabled={!quantity && !recentlyViewed.length && !searchHistory.length} className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl border border-orange-200 bg-orange-50 px-4 py-3 text-sm font-medium text-slate-900 transition hover:bg-orange-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-orange-900 dark:bg-orange-950/30 dark:text-orange-100">
        <Trash2 size={16} />{t.clearShoppingData}
      </button>
    </section>
    <section className="mt-6">
      <h3 className="text-sm font-semibold">{t.supportFaq}</h3>
      <div className="mt-2 space-y-2.5">
        <PanelAction Icon={ShoppingBag} label={t.tracking} onClick={onTrack} />
        <PanelAction Icon={BookOpen} label={t.faqs} onClick={onHelp} />
        <PanelAction Icon={CircleHelp} label={t.support} onClick={onSupport} />
      </div>
    </section>
  </DrawerPanel>
}

function NotificationsPopover({ notifications, products, t, onBrowse, onMarkAllRead }) {
  const unreadCount = notifications.filter((item) => !item.read).length
  return <section role="dialog" aria-label={t.notifications} className="absolute right-0 top-[calc(100%+12px)] z-[75] max-h-[min(75vh,620px)] w-[min(90vw,380px)] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl dark:border-slate-700 dark:bg-slate-900">
    <div className="flex items-center justify-between gap-3">
      <div><h2 className="font-semibold">{t.notifications}</h2><p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{unreadCount} {t.unread}</p></div>
      <button type="button" onClick={onMarkAllRead} disabled={!unreadCount} className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs font-medium text-brand-blue-active hover:bg-blue-50 disabled:opacity-40 dark:hover:bg-slate-800"><CheckCheck size={14} />{t.markAllRead}</button>
    </div>
    {notifications.length === 0 && <div role="status" className="my-4 rounded-xl bg-slate-50 px-3 py-4 text-center dark:bg-slate-800">
      <span className="mx-auto grid size-9 place-items-center rounded-full bg-white text-brand-blue dark:bg-slate-900"><Bell size={17} /></span>
      <p className="mt-2 text-sm font-medium">{t.allCaughtUp}</p><p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t.noActivity}</p>
    </div>}
    {notifications.length > 0 && <div className="mt-3 space-y-2">
      {notifications.slice(0, 8).map((item) => <div key={item.id} className={`rounded-xl border p-3 ${item.read ? 'border-slate-200 dark:border-slate-700' : 'border-blue-200 bg-blue-50/70 dark:border-blue-900 dark:bg-slate-800'}`}>
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-white text-brand-blue dark:bg-slate-900"><ShoppingBag size={15} /></span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium">{item.type === 'status' ? t.orderStatusNotice : t.orderPlacedNotice}</p>
            <p className="mt-1 truncate text-xs text-slate-500 dark:text-slate-300">{item.orderNumber} · {item.status}</p>
          </div>
          {!item.read && <span className="mt-2 size-2 shrink-0 rounded-full bg-brand-orange" aria-label={t.unread} />}
        </div>
      </div>)}
    </div>}
    <div className="mt-3 rounded-xl border border-orange-200 bg-orange-50/70 p-3 dark:border-orange-900 dark:bg-orange-950/20">
      <div className="flex gap-2.5">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-white text-brand-orange dark:bg-slate-900"><Store size={15} /></span>
        <div><p className="text-sm font-medium">{t.storeNotice}</p><p className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-300">{t.announcement}</p></div>
      </div>
    </div>
    <div className="mt-2 rounded-xl border border-slate-200 p-3 dark:border-slate-700">
      <div className="flex gap-2.5">
        <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-blue-50 text-brand-blue dark:bg-slate-800"><Sparkles size={15} /></span>
        <div className="min-w-0 flex-1"><p className="text-sm font-medium">{t.newArrivals}</p><p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-300">{t.newArrivalsBody}</p><p className="mt-1 text-[11px] text-slate-400">{products.length} {t.products.toLowerCase()}</p></div>
      </div>
      <button type="button" onClick={onBrowse} className="mt-3 w-full rounded-lg bg-brand-blue px-3 py-2 text-xs font-semibold text-white transition hover:bg-brand-blue-hover">{t.explore}</button>
    </div>
  </section>
}

function AdminPage({ t, am }) {
  const [token, setToken] = useState(() => sessionStorage.getItem('hikma-admin-token') || '')
  const [authenticated, setAuthenticated] = useState(false)
  const [error, setError] = useState('')
  const [metrics, setMetrics] = useState(null)
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [tab, setTab] = useState('products')
  const [form, setForm] = useState(null)
  const [busy, setBusy] = useState(false)
  const headers = adminHeaders(token)
  const refresh = async () => {
    const [stats, productRows, orderRows] = await Promise.all([
      api('/api/admin/metrics', { headers }),
      api('/api/admin/products', { headers }),
      api('/api/admin/orders', { headers }),
    ])
    setMetrics(stats); setProducts(productRows); setOrders(orderRows)
  }
  const login = async (event) => {
    event.preventDefault(); setError('')
    try {
      await api('/api/admin/session', { method: 'POST', body: JSON.stringify({ token }) })
      sessionStorage.setItem('hikma-admin-token', token)
      await refresh()
      setAuthenticated(true)
    } catch (problem) { setError(problem.message || t.adminLoginError) }
  }
  useEffect(() => {
    if (token) refresh().then(() => setAuthenticated(true)).catch(() => {
      sessionStorage.removeItem('hikma-admin-token')
      setToken('')
    })
  }, [])
  const logout = () => { sessionStorage.removeItem('hikma-admin-token'); setToken(''); setAuthenticated(false) }
  const save = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    const payload = {
      ...form,
      image_id: form.images?.[0] || '',
      price: Number(form.price),
      stock_quantity: Number(form.stock_quantity),
      status: Number(form.stock_quantity) > 0 ? 'In Stock' : 'Out of Stock',
    }
    try {
      await api(form.id ? `/api/admin/products/${form.id}` : '/api/admin/products', {
        method: form.id ? 'PATCH' : 'POST',
        headers,
        body: JSON.stringify(payload),
      })
      await refresh(); setForm(null)
    } catch (problem) { setError(problem.message) }
    finally { setBusy(false) }
  }
  const upload = async (files) => {
    if (!files.length) return
    setBusy(true); setError('')
    try {
      const urls = await Promise.all(Array.from(files).slice(0, 10 - (form.images || []).length).map(async (file) => {
        const data = new FormData(); data.append('file', file)
        return (await api('/api/admin/uploads', { method: 'POST', headers, body: data })).url
      }))
      setForm((current) => ({ ...current, images: [...(current.images || []), ...urls] }))
    } catch (problem) { setError(problem.message) }
    finally { setBusy(false) }
  }
  const updateStatus = async (order, status) => {
    try { await api(`/api/admin/orders/${order.id}`, { method: 'PATCH', headers, body: JSON.stringify({ status }) }); await refresh() }
    catch (problem) { setError(problem.message) }
  }
  const removeProduct = async (product) => {
    if (!window.confirm(`Delete ${product.name_en}?`)) return
    try { await api(`/api/admin/products/${product.id}`, { method: 'DELETE', headers }); await refresh() }
    catch (problem) { setError(problem.message) }
  }
  const emptyProduct = () => ({
    name_en: '', name_am: '', description_en: '', description_am: '',
    price: '', stock_quantity: 0, category: '', images: [],
  })
  if (!authenticated) return <div className="grid min-h-screen place-items-center bg-slate-50 px-4 dark:bg-brand-navy">
    <form onSubmit={login} className="w-full max-w-[390px] rounded-[26px] bg-white p-8 shadow-xl dark:bg-slate-900">
      <a href="/" className="flex items-center gap-3 text-lg font-semibold"><img src="/hikma-logo.png" alt="Hikma Online Shopping" width="64" height="64" className="size-16 bg-white object-contain" /><span>{t.admin}</span></a>
      <h1 className="mt-8 text-2xl font-medium">{t.admin}</h1>
      <Field label={t.token} type="password" value={token} onChange={(event) => setToken(event.target.value)} required />
      {error && <p role="alert" className="mt-4 text-sm text-red-600">{error}</p>}
      <button className="mt-5 w-full rounded-full bg-brand-blue py-3 text-sm font-semibold text-white">{t.signIn}</button>
    </form>
  </div>
  return <div className="min-h-screen bg-slate-50 dark:bg-brand-navy">
    <header className="border-b border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between px-5 py-4 sm:px-8">
        <a href="/" className="flex items-center gap-3 font-semibold"><img src="/hikma-logo.png" alt="Hikma Online Shopping" width="48" height="48" className="size-12 bg-white object-contain" />{t.admin}</a>
        <div className="flex items-center gap-3"><button onClick={() => window.location.href = '/'} className="text-sm text-slate-600">View store ↗</button><button onClick={logout} className="rounded-full border border-slate-200 px-4 py-2 text-sm dark:border-slate-700">{t.signOut}</button></div>
      </div>
    </header>
    <main className="mx-auto max-w-[1440px] px-4 py-8 sm:px-8">
      {metrics && <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 sm:gap-4">
        {[[t.products, metrics.total_products], [t.orders, metrics.total_orders], [t.pending, metrics.pending_orders], [t.revenue, formatPrice(metrics.revenue)]].map(([label, value]) => <div key={label} className="rounded-2xl bg-white p-5 dark:bg-slate-900"><p className="text-xs text-slate-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p></div>)}
      </div>}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex gap-2"><button onClick={() => { setTab('products'); setForm(null) }} className={`rounded-full px-4 py-2.5 text-sm ${tab === 'products' ? 'bg-brand-blue text-white' : 'bg-white dark:bg-slate-900'}`}>{t.products}</button><button onClick={() => { setTab('orders'); setForm(null) }} className={`rounded-full px-4 py-2.5 text-sm ${tab === 'orders' ? 'bg-brand-blue text-white' : 'bg-white dark:bg-slate-900'}`}>{t.orders}</button></div>
        {tab === 'products' && <button onClick={() => setForm(emptyProduct())} className="inline-flex items-center gap-2 rounded-full bg-brand-blue px-5 py-3 text-sm font-semibold text-white"><Plus size={16} />{t.addProduct}</button>}
      </div>
      {error && <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      {form ? <form onSubmit={save} className="mt-6 rounded-2xl bg-white p-5 dark:bg-slate-900 sm:p-7">
        <div className="flex items-center justify-between"><h2 className="text-xl font-medium">{form.id ? t.editProduct : t.addProduct}</h2><button type="button" onClick={() => setForm(null)}><X size={18} /></button></div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2">
          <Field label={t.nameEn} value={form.name_en} onChange={(event) => setForm({ ...form, name_en: event.target.value })} required />
          <Field label={t.nameAm} value={form.name_am} onChange={(event) => setForm({ ...form, name_am: event.target.value })} required />
          <Field label={t.price} type="number" min="0" step="0.01" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required />
          <Field label={t.stock} type="number" min="0" value={form.stock_quantity} onChange={(event) => setForm({ ...form, stock_quantity: event.target.value })} required />
          <Field label={t.category} value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} required />
          <Field label="Size" value={form.size || ''} onChange={(event) => setForm({ ...form, size: event.target.value })} />
          <label className="text-xs font-medium text-slate-600 dark:text-slate-300">{t.descriptionEn}<textarea value={form.description_en || ''} onChange={(event) => setForm({ ...form, description_en: event.target.value })} className="mt-2 min-h-24 w-full rounded-xl border border-slate-200 bg-transparent p-3 text-sm dark:border-slate-700" /></label>
          <label className="text-xs font-medium text-slate-600 dark:text-slate-300">{t.descriptionAm}<textarea value={form.description_am || ''} onChange={(event) => setForm({ ...form, description_am: event.target.value })} className="mt-2 min-h-24 w-full rounded-xl border border-slate-200 bg-transparent p-3 text-sm dark:border-slate-700" /></label>
        </div>
        <label onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); upload(event.dataTransfer.files) }} className="mt-5 flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 px-4 py-5 text-center text-sm text-slate-500">
          <span>{t.uploadHint}</span><input type="file" accept="image/jpeg,image/png,image/webp" multiple className="sr-only" onChange={(event) => upload(event.target.files)} />
        </label>
        {!!form.images?.length && <div className="mt-3 flex gap-3 overflow-x-auto">{form.images.map((image, index) => <div key={`${image}-${index}`} className="relative"><img src={image} alt="" className="size-20 rounded-xl object-cover" /><button type="button" onClick={() => setForm({ ...form, images: form.images.filter((_, position) => position !== index) })} className="absolute -right-2 -top-2 grid size-6 place-items-center rounded-full bg-white text-red-600 shadow"><X size={13} /></button></div>)}</div>}
        <button disabled={busy} className="mt-6 rounded-full bg-brand-blue px-6 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? '…' : t.saveProduct}</button>
      </form> : tab === 'products' ? <div className="mt-5 overflow-hidden rounded-2xl bg-white dark:bg-slate-900">
        <div className="divide-y divide-slate-200 dark:divide-slate-700">        {products.map((product) => <div key={product.id} className="flex items-center gap-3 px-4 py-4 sm:px-6"><img src={product.images?.[0]} alt="" className="size-12 rounded-lg bg-slate-100 object-cover dark:bg-slate-800" /><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{product.name_en}</p><p className="mt-1 text-xs text-slate-500">{formatPrice(product.price)} · {product.stock_quantity} in stock</p></div><button onClick={() => setForm({ ...product, images: product.image_refs || [] })} className="rounded-full border border-slate-200 px-3 py-2 text-xs dark:border-slate-700">{t.editProduct}</button><button onClick={() => removeProduct(product)} className="grid size-9 place-items-center rounded-full text-red-600 hover:bg-red-50" aria-label="Delete"><Trash2 size={15} /></button></div>)}</div>
      </div> : <div className="mt-5 space-y-3">{orders.map((order) => <div key={order.id} className="rounded-2xl bg-white p-5 dark:bg-slate-900"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="text-sm font-semibold">{order.order_number}</p><p className="mt-1 text-xs text-slate-500">{t.customer}: {order.customer_name} · {order.customer_phone}</p></div><div className="text-right"><p className="text-sm font-semibold">{formatPrice(order.final_amount)}</p><p className="mt-1 text-xs text-slate-500">{order.status}</p></div></div><div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-slate-500">{(order.items || []).map((item) => `${item.name_en} × ${item.quantity}`).join(' · ')}</p><label className="flex items-center gap-2 text-xs"><span>{t.status}</span><select value={order.status} onChange={(event) => updateStatus(order, event.target.value)} className="rounded-lg border border-slate-200 bg-transparent px-3 py-2 dark:border-slate-700">{['Pending', 'Confirmed', 'Shipped', 'Delivered'].map((status) => <option key={status}>{status}</option>)}</select></label></div></div>)}</div>}
    </main>
  </div>
}

export default App
