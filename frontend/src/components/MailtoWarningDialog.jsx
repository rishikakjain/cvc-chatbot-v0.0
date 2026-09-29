import React from 'react'
import { useLang } from '../i18n'

export default function MailtoWarningDialog({ href, onClose }) {
  const { t } = useLang()
  return (
    <div className="mailto-overlay" role="dialog" aria-modal="true">
      <div className="mailto-dialog">
        <h3 className="mailto-dialog__title">{t('mailto_warning_title')}</h3>
        <p className="mailto-dialog__body">{t('mailto_warning_body')}</p>
        <div className="mailto-dialog__actions">
          <button
            className="mailto-dialog__cancel"
            onClick={onClose}
            type="button"
          >
            {t('mailto_warning_cancel')}
          </button>
          <a
            className="mailto-dialog__confirm"
            href={href}
            onClick={onClose}
          >
            {t('mailto_warning_confirm')}
          </a>
        </div>
      </div>
    </div>
  )
}
