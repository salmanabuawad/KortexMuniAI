import {
  AppBar,
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  Chip,
  IconButton,
  Tooltip,
} from "@mui/material";
import ChatIcon from "@mui/icons-material/ChatBubbleOutline";
import SearchIcon from "@mui/icons-material/Search";
import KnowledgeIcon from "@mui/icons-material/MenuBook";
import DocumentsIcon from "@mui/icons-material/Description";
import AgentsIcon from "@mui/icons-material/SmartToy";
import VehiclesIcon from "@mui/icons-material/DirectionsCar";
import AdminIcon from "@mui/icons-material/Settings";
import LogoutIcon from "@mui/icons-material/Logout";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../auth/AuthContext";
import { LanguageSwitcher } from "../components/LanguageSwitcher";

const DRAWER_WIDTH = 248;

interface NavItem {
  to: string;
  labelKey: string;
  icon: JSX.Element;
  later?: boolean;
}

const NAV: NavItem[] = [
  { to: "/chat", labelKey: "nav.chat", icon: <ChatIcon /> },
  { to: "/search", labelKey: "nav.search", icon: <SearchIcon />, later: true },
  { to: "/knowledge", labelKey: "nav.knowledge", icon: <KnowledgeIcon />, later: true },
  { to: "/documents", labelKey: "nav.documents", icon: <DocumentsIcon /> },
  { to: "/agents", labelKey: "nav.agents", icon: <AgentsIcon />, later: true },
  { to: "/vehicles", labelKey: "nav.vehicles", icon: <VehiclesIcon />, later: true },
  { to: "/admin", labelKey: "nav.admin", icon: <AdminIcon />, later: true },
];

export function AppLayout() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{ zIndex: (th) => th.zIndex.drawer + 1, borderBottom: 1, borderColor: "divider" }}
      >
        <Toolbar sx={{ gap: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "primary.main" }}>
            MuniAI
          </Typography>
          <Chip size="small" color="success" variant="outlined" label={t("chat.localBadge")} />
          <Box sx={{ flexGrow: 1 }} />
          <LanguageSwitcher />
          <Typography variant="body2" sx={{ mx: 1 }}>
            {user?.full_name}
          </Typography>
          <Tooltip title={t("common.logout")}>
            <IconButton onClick={logout} size="small">
              <LogoutIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: "auto" }}>
          <List>
            {NAV.map((item) => (
              <ListItemButton
                key={item.to}
                selected={location.pathname === item.to}
                onClick={() => navigate(item.to)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={t(item.labelKey)} />
                {item.later && (
                  <Chip size="small" variant="outlined" label={t("common.comingLater")} />
                )}
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 0, bgcolor: "background.default" }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
