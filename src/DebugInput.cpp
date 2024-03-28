#include "DebugInput.h"
#include "ButtonsTask.h"

extern "C"
{
    #include "AppHardwareApi.h"
    #include "zcl_options.h"
}

DebugInput::DebugInput()
{
    reset();
}

void DebugInput::reset()
{
    ptr = buf;
    hasData = false;
}

void DebugInput::handleDebugInput()
{
    // Avoid buffer overrun
    if(ptr >= buf + BUF_SIZE)
        return;

    // Receive the next symbol, if any
    while(u16AHI_UartReadRxFifoLevel(E_AHI_UART_0) > 0)
    {
        char ch;
        u16AHI_UartBlockReadData(E_AHI_UART_0, (uint8*)&ch, 1);

        if(ch == '\r' || ch == '\n')
        {
            *ptr = 0;
            hasData = true;
        }
        else
            *ptr = ch;

        ptr++;
    }
}

bool DebugInput::hasCompletedLine() const
{
    return hasData;
}

bool DebugInput::matchCommand(const char * command) const
{
    int len = strlen(command);
    if(strncmp(command, buf, len) == 0 && buf[len] == 0)
        return true;

    return false;
}

void APP_vHandleDebugInput(DebugInput & debugInput)
{
    debugInput.handleDebugInput();
    if(debugInput.hasCompletedLine())
    {
        if(debugInput.matchCommand("BTN1_PRESS"))
        {
            ButtonsTask::getInstance()->setButtonsOverride(SWITCH1_BTN_MASK);
            DBG_vPrintf(TRUE, "Matched BTN1_PRESS\n");
        }

#ifdef SWITCH2_BTN_PIN
        if(debugInput.matchCommand("BTN2_PRESS"))
        {
            ButtonsTask::getInstance()->setButtonsOverride(SWITCH2_BTN_MASK);
            DBG_vPrintf(TRUE, "Matched BTN2_PRESS\n");
        }

        if(debugInput.matchCommand("BTN3_PRESS"))   // Use button #3 to indicate both buttons
        {
            ButtonsTask::getInstance()->setButtonsOverride(SWITCH1_BTN_MASK | SWITCH2_BTN_MASK);
            DBG_vPrintf(TRUE, "Matched BTN3_PRESS\n");
        }
#endif

        if(debugInput.matchCommand("BTN1_RELEASE") || debugInput.matchCommand("BTN2_RELEASE") || debugInput.matchCommand("BTN3_RELEASE"))
        {
            ButtonsTask::getInstance()->setButtonsOverride(0);
            DBG_vPrintf(TRUE, "Matched BTNx_RELEASE\n");
        }

        debugInput.reset();
    }
}
