"""Scrapers package for Multi-Platform job collection."""
from core.scrapers.base import BaseScraper
from core.scrapers.linkedin_scraper import LinkedInScraper
from core.scrapers.kariyernet_scraper import KariyerNetScraper
from core.scrapers.manager import JobScraperManager

__all__ = ["BaseScraper", "LinkedInScraper", "KariyerNetScraper", "JobScraperManager"]
